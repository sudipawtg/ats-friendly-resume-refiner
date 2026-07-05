"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, FileText, FlaskConical, Layers, Plus } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { fetchBatches, fetchCVProjects } from "@/lib/api";

const QUICK_ACTIONS = [
  {
    href: "/playground",
    icon: FlaskConical,
    title: "Tailor for a job",
    description: "Match your CV to one role",
    color: "text-brand-600",
    bg: "bg-brand-500/10",
    testId: "action-tailor",
  },
  {
    href: "/cvs",
    icon: FileText,
    title: "Upload CV",
    description: "Add your master LaTeX project",
    color: "text-brand-accent",
    bg: "bg-violet-500/10",
    testId: "action-upload",
  },
  {
    href: "/batch",
    icon: Layers,
    title: "Bulk campaign",
    description: "Tailor for many jobs at once",
    color: "text-apple-indigo",
    bg: "bg-indigo-500/10",
    testId: "action-batch",
  },
] as const;

export default function DashboardPage() {
  const { data: projects = [] } = useQuery({ queryKey: ["cvs"], queryFn: fetchCVProjects });
  const { data: batches = [] } = useQuery({ queryKey: ["batches"], queryFn: fetchBatches });

  const completedJobs = batches.reduce((sum, batch) => sum + batch.completed, 0);
  const hasProjects = projects.length > 0;

  return (
    <div data-testid="dashboard-page">
      <PageHeader
        title={hasProjects ? "Welcome back" : "Get started"}
        subtitle={hasProjects ? "Pick up where you left off." : "Upload a CV, then tailor it for any job."}
        action={
          hasProjects ? (
            <Link href="/playground" className="glass-button-primary">
              <Plus size={16} />
              New tailoring
            </Link>
          ) : (
            <Link href="/cvs" className="glass-button-primary">
              <Plus size={16} />
              Upload CV
            </Link>
          )
        }
      />

      <div className="mb-8 grid grid-cols-3 gap-3 sm:gap-4">
        <div className="stat-card" data-testid="stat-cvs">
          <span className="stat-value">{projects.length}</span>
          <span className="stat-label">CVs</span>
        </div>
        <div className="stat-card" data-testid="stat-batches">
          <span className="stat-value">{batches.length}</span>
          <span className="stat-label">Campaigns</span>
        </div>
        <div className="stat-card" data-testid="stat-jobs">
          <span className="stat-value">{completedJobs}</span>
          <span className="stat-label">Done</span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {QUICK_ACTIONS.map((action) => {
          const Icon = action.icon;
          return (
            <Link
              key={action.href}
              href={action.href}
              className="glass-card-interactive group flex items-center gap-4 p-5"
              data-testid={action.testId}
            >
              <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-apple-lg ${action.bg}`}>
                <Icon className={action.color} size={22} strokeWidth={2} />
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="text-apple-headline text-apple-label">{action.title}</h2>
                <p className="text-apple-footnote text-apple-label-secondary">{action.description}</p>
              </div>
              <ArrowRight
                size={16}
                className="shrink-0 text-apple-label-tertiary transition-transform group-hover:translate-x-0.5"
              />
            </Link>
          );
        })}
      </div>

      {batches.length > 0 ? (
        <section className="mt-8">
          <h2 className="section-title mb-3">Recent campaigns</h2>
          <div className="space-y-2">
            {batches.slice(0, 5).map((batch) => (
              <Link
                key={batch.id}
                href={`/batch?id=${batch.id}`}
                className="glass-card-interactive flex items-center justify-between px-5 py-3.5"
                data-testid={`batch-row-${batch.id}`}
              >
                <div className="min-w-0">
                  <p className="truncate text-apple-headline text-apple-label">{batch.name}</p>
                  <p className="text-apple-footnote text-apple-label-secondary">
                    {batch.completed}/{batch.total_jobs} complete
                  </p>
                </div>
                <span className="glass-badge-blue shrink-0">{batch.status}</span>
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
