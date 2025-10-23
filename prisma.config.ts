import "dotenv/config";
import { PrismaClient } from "@prisma/client";

// Prisma configuration
export const prisma = new PrismaClient({
  log: ["query", "error", "warn"],
});
