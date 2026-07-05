"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import Link from "next/link";
import { buildPlaygroundUrl } from "@/features/playground/playground.logic";
import {
  AlertCircle,
  Calendar,
  ClipboardCopy,
  ExternalLink,
  Layers,
  MapPin,
  Search,
} from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import {
  fetchDateFilters,
  fetchJobSearchSources,
  searchJobs,
  type JobListingResult,
  type JobSearchResponse,
} from "@/lib/api";

const DEFAULT_SOURCES = ["reed_uk", "remotive", "arbeitnow"];

export default function DiscoverPage() {
  const [jobTitle, setJobTitle] = useState("");
  const [location, setLocation] = useState("London, UK");
  const [maxDaysOld, setMaxDaysOld] = useState(7);
  const [selectedSources, setSelectedSources] = useState<string[]>(DEFAULT_SOURCES);
  const [searchResult, setSearchResult] = useState<JobSearchResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const { data: sources = {} } = useQuery({
    queryKey: ["job-search-sources"],
    queryFn: fetchJobSearchSources,
  });

  const { data: dateFilters = {} } = useQuery({
    queryKey: ["date-filters"],
    queryFn: fetchDateFilters,
  });

  const searchMutation = useMutation({
    mutationFn: () =>
      searchJobs({
        job_title: jobTitle.trim(),
        location,
        max_days_old: maxDaysOld,
        sources: selectedSources,
        max_results_per_source: 20,
      }),
    onSuccess: (data) => {
      setSearchResult(data);
      setError("");
    },
    onError: (err: Error) => setError(err.message),
  });

  const handleToggleSource = useCallback((sourceKey: string) => {
    setSelectedSources((prev) =>
      prev.includes(sourceKey) ? prev.filter((key) => key !== sourceKey) : [...prev, sourceKey]
    );
  }, []);

  const handleSearch = useCallback(() => {
    if (!jobTitle.trim()) {
      setError("Enter a job title.");
      return;
    }
    if (selectedSources.length === 0) {
      setError("Select at least one site.");
      return;
    }
    searchMutation.mutate();
  }, [jobTitle, selectedSources, searchMutation]);

  const handleCopyUrls = useCallback(async () => {
    if (!searchResult) return;
    const urls = searchResult.results.map((job) => job.url).join("\n");
    await navigator.clipboard.writeText(urls);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [searchResult]);

  const handleSendToBatch = useCallback(() => {
    if (!searchResult) return;
    const urls = searchResult.results.map((job) => job.url).join("\n");
    sessionStorage.setItem("resumeforge_batch_urls", urls);
    window.location.href = "/batch";
  }, [searchResult]);

  return (
    <div data-testid="discover-page">
      <PageHeader title="Discover" subtitle="Find jobs across multiple boards." />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="glass-card lg:col-span-1">
          <label className="field-label">Job title</label>
          <input
            type="text"
            value={jobTitle}
            onChange={(event) => setJobTitle(event.target.value)}
            placeholder="AI Engineer"
            className="glass-input mb-3"
            data-testid="discover-job-title"
          />

          <label className="field-label">Location</label>
          <input
            type="text"
            value={location}
            onChange={(event) => setLocation(event.target.value)}
            className="glass-input mb-3"
            data-testid="discover-location"
          />

          <label className="field-label">Posted within</label>
          <select
            value={maxDaysOld}
            onChange={(event) => setMaxDaysOld(Number(event.target.value))}
            className="glass-input mb-4"
            data-testid="discover-date-filter"
          >
            {Object.entries(dateFilters).map(([label, days]) => (
              <option key={label} value={days}>
                {days} day{days === 1 ? "" : "s"}
              </option>
            ))}
          </select>

          <p className="field-label">Sites</p>
          <div className="mb-4 flex flex-wrap gap-2">
            {Object.entries(sources).map(([key, label]) => {
              const isSelected = selectedSources.includes(key);
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => handleToggleSource(key)}
                  className={`rounded-full px-3 py-1 text-apple-caption font-medium transition-colors ${
                    isSelected
                      ? "bg-apple-blue/12 text-apple-blue"
                      : "bg-apple-surface-secondary text-apple-label-secondary"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={handleSearch}
            disabled={searchMutation.isPending}
            className="glass-button-primary w-full"
            data-testid="discover-search-btn"
          >
            <Search size={16} />
            {searchMutation.isPending ? "Searching…" : "Search"}
          </button>

          {error ? (
            <div className="alert-error mt-3">
              <AlertCircle size={16} className="shrink-0" /> {error}
            </div>
          ) : null}
        </div>

        <div className="lg:col-span-2">
          {searchMutation.isPending ? (
            <div className="glass-card py-16 text-center text-apple-subheadline text-apple-blue" data-testid="discover-loading">
              Searching…
            </div>
          ) : null}

          {!searchMutation.isPending && !searchResult ? (
            <EmptyState icon={Search} title="Search for roles" description="Enter a title and hit Search." />
          ) : null}

          {searchResult && !searchMutation.isPending ? (
            <div className="space-y-3">
              <div className="glass-card flex flex-wrap items-center justify-between gap-3 py-3">
                <p className="text-apple-headline text-apple-label">
                  {searchResult.total_results} result{searchResult.total_results === 1 ? "" : "s"}
                </p>
                <div className="flex gap-2">
                  <button type="button" onClick={handleCopyUrls} className="glass-button text-sm" data-testid="copy-urls-btn">
                    <ClipboardCopy size={14} />
                    {copied ? "Copied" : "Copy URLs"}
                  </button>
                  <button type="button" onClick={handleSendToBatch} className="glass-button-primary text-sm" data-testid="send-batch-btn">
                    <Layers size={14} /> Campaign
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                {searchResult.results.map((job) => (
                  <JobResultCard key={job.id} job={job} />
                ))}
              </div>

              {searchResult.results.length === 0 ? (
                <EmptyState icon={Search} title="No results" description="Try a broader title or longer date range." />
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function JobResultCard({ job }: { job: JobListingResult }) {
  const dateLabel =
    job.posted_days_ago === 0
      ? "Today"
      : job.posted_days_ago != null
        ? `${job.posted_days_ago}d ago`
        : job.posted_date || "—";

  return (
    <div className="glass-card-interactive py-3.5" data-testid={`job-result-${job.id}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span className="glass-badge-blue">{job.source_label || job.source}</span>
            <span className="flex items-center gap-1 text-apple-caption text-apple-label-tertiary">
              <Calendar size={11} /> {dateLabel}
            </span>
          </div>
          <h3 className="text-apple-headline text-apple-label">{job.title}</h3>
          {(job.company || job.location) && (
            <p className="mt-0.5 flex flex-wrap items-center gap-1 text-apple-footnote text-apple-label-secondary">
              {job.company}
              {job.company && job.location ? " · " : null}
              {job.location ? (
                <span className="inline-flex items-center gap-0.5">
                  <MapPin size={12} /> {job.location}
                </span>
              ) : null}
            </p>
          )}
        </div>
        <div className="flex shrink-0 gap-2">
          <a href={job.url} target="_blank" rel="noopener noreferrer" className="glass-button p-2" data-testid={`job-link-${job.id}`}>
            <ExternalLink size={14} />
          </a>
          <Link
            href={buildPlaygroundUrl({ url: job.url, title: job.title, company: job.company })}
            className="glass-button-primary text-sm"
            data-testid={`playground-link-${job.id}`}
          >
            Tailor
          </Link>
        </div>
      </div>
    </div>
  );
}
