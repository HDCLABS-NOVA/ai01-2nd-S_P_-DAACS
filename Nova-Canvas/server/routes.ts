import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { setupAuth, isAuthenticated } from "./replitAuth";
import { chatWithNova } from "./openai";
import { insertProjectSchema, insertMessageSchema } from "@shared/schema";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  // Auth middleware
  await setupAuth(app);

  // Auth routes
  app.get("/api/auth/user", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const user = await storage.getUser(userId);
      res.json(user);
    } catch (error) {
      console.error("Error fetching user:", error);
      res.status(500).json({ message: "Failed to fetch user" });
    }
  });

  // Project routes
  app.get("/api/projects", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const projects = await storage.getProjectsByUser(userId);
      res.json(projects);
    } catch (error) {
      console.error("Error fetching projects:", error);
      res.status(500).json({ message: "Failed to fetch projects" });
    }
  });

  app.get("/api/projects/:id", isAuthenticated, async (req: any, res) => {
    try {
      const projectId = parseInt(req.params.id);
      const project = await storage.getProject(projectId);
      
      if (!project) {
        return res.status(404).json({ message: "Project not found" });
      }

      // Verify ownership
      const userId = req.user.claims.sub;
      if (project.userId !== userId) {
        return res.status(403).json({ message: "Forbidden" });
      }

      res.json(project);
    } catch (error) {
      console.error("Error fetching project:", error);
      res.status(500).json({ message: "Failed to fetch project" });
    }
  });

  app.post("/api/projects", isAuthenticated, async (req: any, res) => {
    try {
      const userId = req.user.claims.sub;
      const data = { ...req.body, userId };
      
      const parsed = insertProjectSchema.safeParse(data);
      if (!parsed.success) {
        return res.status(400).json({ message: "Invalid project data", errors: parsed.error.errors });
      }

      const project = await storage.createProject(parsed.data);

      // Create initial message
      await storage.createMessage({
        projectId: project.id,
        role: "user",
        content: project.requirement,
      });

      // Create DAACS's initial response
      await storage.createMessage({
        projectId: project.id,
        role: "daacs",
        content: "요청 잘 받았어요! 사용할 LLM과 개발 영역(프론트엔드/백엔드/오케스트레이터)을 알려주세요.",
      });

      res.json(project);
    } catch (error) {
      console.error("Error creating project:", error);
      res.status(500).json({ message: "Failed to create project" });
    }
  });

  // Messages routes
  app.get("/api/projects/:id/messages", isAuthenticated, async (req: any, res) => {
    try {
      const projectId = parseInt(req.params.id);
      const project = await storage.getProject(projectId);
      
      if (!project || project.userId !== req.user.claims.sub) {
        return res.status(403).json({ message: "Forbidden" });
      }

      const messages = await storage.getMessagesByProject(projectId);
      res.json(messages);
    } catch (error) {
      console.error("Error fetching messages:", error);
      res.status(500).json({ message: "Failed to fetch messages" });
    }
  });

  // Chat with NOVA
  app.post("/api/projects/:id/chat", isAuthenticated, async (req: any, res) => {
    try {
      const projectId = parseInt(req.params.id);
      
      // Validate request body
      const messageData = insertMessageSchema.omit({ projectId: true }).safeParse({
        role: "user",
        content: req.body?.content,
      });

      if (!messageData.success) {
        return res.status(400).json({ message: "Invalid message content", errors: messageData.error.errors });
      }

      const { content } = messageData.data;

      const project = await storage.getProject(projectId);
      if (!project || project.userId !== req.user.claims.sub) {
        return res.status(403).json({ message: "Forbidden" });
      }

      // Save user message
      const userMessage = await storage.createMessage({
        projectId,
        role: "user",
        content,
      });

      // Get conversation history
      const allMessages = await storage.getMessagesByProject(projectId);
      const conversationHistory = allMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // Get current plan
      const plans = await storage.getPlansByProject(projectId);
      const currentPlan = plans.length > 0 ? plans[0].content : undefined;

      // Chat with DAACS
      const novaResponse = await chatWithNova(
        content,
        project.requirement,
        conversationHistory,
        currentPlan
      );

      // Save DAACS's response
      const novaMessage = await storage.createMessage({
        projectId,
        role: "daacs",
        content: novaResponse.response,
      });

      // Update project with LLM model and development area if provided
      if (novaResponse.llmModel || novaResponse.developmentArea) {
        await storage.updateProject(projectId, {
          llmModel: novaResponse.llmModel || project.llmModel,
          developmentArea: novaResponse.developmentArea || project.developmentArea,
        });
      }

      // Create or update plan if provided
      if (novaResponse.plan) {
        const existingPlans = await storage.getPlansByProject(projectId);
        const oldPlan = existingPlans.length > 0 ? existingPlans[0] : null;

        await storage.createPlan({
          projectId,
          content: novaResponse.plan,
          version: 1,
        });

        // Log plan change
        await storage.createLog({
          projectId,
          type: "plan_change",
          content: oldPlan ? "플랜이 수정되었습니다." : "새 플랜이 생성되었습니다.",
          metadata: oldPlan ? { previousVersion: oldPlan.version } : null,
        });
      }

      // Save code snippet if provided
      if (novaResponse.code) {
        await storage.createCodeSnippet({
          projectId,
          filename: novaResponse.code.filename,
          language: novaResponse.code.language,
          content: novaResponse.code.content,
          description: novaResponse.code.description,
        });

        // Log code generation
        await storage.createLog({
          projectId,
          type: "code_generated",
          content: `코드 생성됨: ${novaResponse.code.filename}`,
          metadata: { language: novaResponse.code.language },
        });
      }

      // Update preview state if provided
      if (novaResponse.preview) {
        await storage.upsertPreviewState({
          projectId,
          htmlContent: novaResponse.preview.htmlContent,
          cssContent: novaResponse.preview.cssContent,
          jsContent: novaResponse.preview.jsContent,
          description: novaResponse.preview.description,
        });
      }

      res.json({
        response: novaResponse.response,
        messageId: novaMessage.id,
      });
    } catch (error) {
      console.error("Error in chat:", error);
      res.status(500).json({ message: "Failed to process message" });
    }
  });

  // Plans routes
  app.get("/api/projects/:id/plans", isAuthenticated, async (req: any, res) => {
    try {
      const projectId = parseInt(req.params.id);
      const project = await storage.getProject(projectId);
      
      if (!project || project.userId !== req.user.claims.sub) {
        return res.status(403).json({ message: "Forbidden" });
      }

      const plans = await storage.getPlansByProject(projectId);
      res.json(plans);
    } catch (error) {
      console.error("Error fetching plans:", error);
      res.status(500).json({ message: "Failed to fetch plans" });
    }
  });

  // Code snippets routes
  app.get("/api/projects/:id/code-snippets", isAuthenticated, async (req: any, res) => {
    try {
      const projectId = parseInt(req.params.id);
      const project = await storage.getProject(projectId);
      
      if (!project || project.userId !== req.user.claims.sub) {
        return res.status(403).json({ message: "Forbidden" });
      }

      const snippets = await storage.getCodeSnippetsByProject(projectId);
      res.json(snippets);
    } catch (error) {
      console.error("Error fetching code snippets:", error);
      res.status(500).json({ message: "Failed to fetch code snippets" });
    }
  });

  // Logs routes
  app.get("/api/projects/:id/logs", isAuthenticated, async (req: any, res) => {
    try {
      const projectId = parseInt(req.params.id);
      const project = await storage.getProject(projectId);
      
      if (!project || project.userId !== req.user.claims.sub) {
        return res.status(403).json({ message: "Forbidden" });
      }

      const projectLogs = await storage.getLogsByProject(projectId);
      res.json(projectLogs);
    } catch (error) {
      console.error("Error fetching logs:", error);
      res.status(500).json({ message: "Failed to fetch logs" });
    }
  });

  // Preview state routes
  app.get("/api/projects/:id/preview", isAuthenticated, async (req: any, res) => {
    try {
      const projectId = parseInt(req.params.id);
      const project = await storage.getProject(projectId);
      
      if (!project || project.userId !== req.user.claims.sub) {
        return res.status(403).json({ message: "Forbidden" });
      }

      const previewState = await storage.getPreviewState(projectId);
      res.json(previewState || null);
    } catch (error) {
      console.error("Error fetching preview state:", error);
      res.status(500).json({ message: "Failed to fetch preview state" });
    }
  });

  return httpServer;
}
