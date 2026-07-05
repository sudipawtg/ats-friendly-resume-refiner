import { redirect } from "next/navigation";

interface TailorRedirectPageProps {
  searchParams: Promise<{ url?: string; cvId?: string }>;
}

export default async function TailorRedirectPage({ searchParams }: TailorRedirectPageProps) {
  const params = await searchParams;
  const query = new URLSearchParams();
  if (params.url) query.set("url", params.url);
  if (params.cvId) query.set("cvId", params.cvId);
  const suffix = query.toString();
  redirect(suffix ? `/playground?${suffix}` : "/playground");
}
