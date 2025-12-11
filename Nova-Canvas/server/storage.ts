import {
  users,
  projects,
  plans,
  messages,
  codeSnippets,
  logs,
  previewStates,
  type User,
  type UpsertUser,
  type Project,
  type InsertProject,
  type Plan,
  type InsertPlan,
  type Message,
  type InsertMessage,
  type CodeSnippet,
  type InsertCodeSnippet,
  type Log,
  type InsertLog,
  type PreviewState,
  type InsertPreviewState,
} from "@shared/schema";
// import { db } from "./db";
import { eq, desc } from "drizzle-orm";

export interface IStorage {
  // User operations (mandatory for Replit Auth)
  getUser(id: string): Promise<User | undefined>;
  upsertUser(user: UpsertUser): Promise<User>;

  // Project operations
  getProject(id: number): Promise<Project | undefined>;
  getProjectsByUser(userId: string): Promise<Project[]>;
  createProject(project: InsertProject): Promise<Project>;
  updateProject(id: number, data: Partial<InsertProject>): Promise<Project | undefined>;

  // Plan operations
  getPlansByProject(projectId: number): Promise<Plan[]>;
  createPlan(plan: InsertPlan): Promise<Plan>;

  // Message operations
  getMessagesByProject(projectId: number): Promise<Message[]>;
  createMessage(message: InsertMessage): Promise<Message>;

  // Code snippet operations
  getCodeSnippetsByProject(projectId: number): Promise<CodeSnippet[]>;
  createCodeSnippet(snippet: InsertCodeSnippet): Promise<CodeSnippet>;

  // Log operations
  getLogsByProject(projectId: number): Promise<Log[]>;
  createLog(log: InsertLog): Promise<Log>;

  // Preview state operations
  getPreviewState(projectId: number): Promise<PreviewState | undefined>;
  upsertPreviewState(state: InsertPreviewState): Promise<PreviewState>;
}

export class MemStorage implements IStorage {
  private users: Map<string, User>;
  private projects: Map<number, Project>;
  private plans: Map<number, Plan>;
  private messages: Map<number, Message>;
  private codeSnippets: Map<number, CodeSnippet>;
  private logs: Map<number, Log>;
  private previewStates: Map<number, PreviewState>;

  private currentProjectId: number;
  private currentPlanId: number;
  private currentMessageId: number;
  private currentSnippetId: number;
  private currentLogId: number;
  private currentPreviewId: number;

  constructor() {
    this.users = new Map();
    this.projects = new Map();
    this.plans = new Map();
    this.messages = new Map();
    this.codeSnippets = new Map();
    this.logs = new Map();
    this.previewStates = new Map();

    this.currentProjectId = 1;
    this.currentPlanId = 1;
    this.currentMessageId = 1;
    this.currentSnippetId = 1;
    this.currentLogId = 1;
    this.currentPreviewId = 1;
  }

  // User operations
  async getUser(id: string): Promise<User | undefined> {
    return this.users.get(id);
  }

  async upsertUser(userData: UpsertUser): Promise<User> {
    const id = userData.id || "local-user";
    const user: User = {
      ...userData,
      id,
      createdAt: new Date(),
      updatedAt: new Date(),
    } as User;
    this.users.set(id, user);
    return user;
  }

  // Project operations
  async getProject(id: number): Promise<Project | undefined> {
    return this.projects.get(id);
  }

  async getProjectsByUser(userId: string): Promise<Project[]> {
    return Array.from(this.projects.values())
      .filter((p) => p.userId === userId)
      .sort((a, b) => (b.updatedAt?.getTime() || 0) - (a.updatedAt?.getTime() || 0));
  }

  async createProject(project: InsertProject): Promise<Project> {
    const id = this.currentProjectId++;
    const newProject: Project = {
      ...project,
      id,
      createdAt: new Date(),
      updatedAt: new Date(),
    } as Project;
    this.projects.set(id, newProject);
    return newProject;
  }

  async updateProject(id: number, data: Partial<InsertProject>): Promise<Project | undefined> {
    const project = this.projects.get(id);
    if (!project) return undefined;

    const updatedProject = { ...project, ...data, updatedAt: new Date() };
    this.projects.set(id, updatedProject);
    return updatedProject;
  }

  // Plan operations
  async getPlansByProject(projectId: number): Promise<Plan[]> {
    return Array.from(this.plans.values())
      .filter((p) => p.projectId === projectId)
      .sort((a, b) => b.version - a.version);
  }

  async createPlan(plan: InsertPlan): Promise<Plan> {
    const id = this.currentPlanId++;
    const existingPlans = await this.getPlansByProject(plan.projectId);
    const nextVersion = existingPlans.length > 0 ? Math.max(...existingPlans.map((p) => p.version)) + 1 : 1;

    const newPlan: Plan = {
      ...plan,
      id,
      version: nextVersion,
      createdAt: new Date(),
    } as Plan;
    this.plans.set(id, newPlan);
    return newPlan;
  }

  // Message operations
  async getMessagesByProject(projectId: number): Promise<Message[]> {
    return Array.from(this.messages.values())
      .filter((m) => m.projectId === projectId)
      .sort((a, b) => (a.createdAt?.getTime() || 0) - (b.createdAt?.getTime() || 0));
  }

  async createMessage(message: InsertMessage): Promise<Message> {
    const id = this.currentMessageId++;
    const newMessage: Message = {
      ...message,
      id,
      createdAt: new Date(),
    } as Message;
    this.messages.set(id, newMessage);
    return newMessage;
  }

  // Code snippet operations
  async getCodeSnippetsByProject(projectId: number): Promise<CodeSnippet[]> {
    return Array.from(this.codeSnippets.values())
      .filter((s) => s.projectId === projectId)
      .sort((a, b) => (b.createdAt?.getTime() || 0) - (a.createdAt?.getTime() || 0));
  }

  async createCodeSnippet(snippet: InsertCodeSnippet): Promise<CodeSnippet> {
    const id = this.currentSnippetId++;
    const newSnippet: CodeSnippet = {
      ...snippet,
      id,
      createdAt: new Date(),
    } as CodeSnippet;
    this.codeSnippets.set(id, newSnippet);
    return newSnippet;
  }

  // Log operations
  async getLogsByProject(projectId: number): Promise<Log[]> {
    return Array.from(this.logs.values())
      .filter((l) => l.projectId === projectId)
      .sort((a, b) => (b.createdAt?.getTime() || 0) - (a.createdAt?.getTime() || 0));
  }

  async createLog(log: InsertLog): Promise<Log> {
    const id = this.currentLogId++;
    const newLog: Log = {
      ...log,
      id,
      createdAt: new Date(),
    } as Log;
    this.logs.set(id, newLog);
    return newLog;
  }

  // Preview state operations
  async getPreviewState(projectId: number): Promise<PreviewState | undefined> {
    return Array.from(this.previewStates.values()).find((p) => p.projectId === projectId);
  }

  async upsertPreviewState(state: InsertPreviewState): Promise<PreviewState> {
    const existing = await this.getPreviewState(state.projectId);
    const id = existing ? existing.id : this.currentPreviewId++;

    const newState: PreviewState = {
      ...state,
      id,
      updatedAt: new Date(),
    } as PreviewState;
    this.previewStates.set(id, newState);
    return newState;
  }
}

export const storage = new MemStorage();
