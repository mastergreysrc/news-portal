const BASE = '/api';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
	const token = localStorage.getItem('token');
	const headers: Record<string, string> = { 'Content-Type': 'application/json' };
	if (token) headers['Authorization'] = `Bearer ${token}`;
	if (options?.headers) {
		if (options.headers instanceof Headers) {
			options.headers.forEach((value, key) => { headers[key] = value; });
		} else {
			Object.assign(headers, options.headers as Record<string, string>);
		}
		delete (options as Record<string, unknown>).headers;
	}
	const res = await fetch(`${BASE}${url}`, { ...options, headers });
	if (!res.ok) throw new Error(await res.text());
	return res.json();
}

export interface Category { id: number; name: string; slug: string; icon: string; }
export interface SourceRef { type: string; name: string; url: string; }
export interface NewsCluster {
	id: number; canonical_title: string; canonical_summary: string | null;
	popularity_score: number; fire_tier: number; source_count: number;
	sources: SourceRef[]; published_at: string | null; category: Category;
	is_favorited: boolean; created_at: string | null;
}

export function getCategories(): Promise<Category[]> { return fetchJSON('/categories'); }
export function getNews(params: Record<string, string> = {}): Promise<{items: NewsCluster[], pagination: {page: number, per_page: number, total: number, pages: number}}> {
	const qs = new URLSearchParams(params).toString();
	return fetchJSON(`/news${qs ? '?' + qs : ''}`);
}
export function getDailyNews(date: string): Promise<Record<string, NewsCluster[]>> {
	return fetchJSON(`/news/daily/${date}`);
}
export function searchNews(q: string, page = 1): Promise<{items: NewsCluster[], pagination: {page: number, per_page: number, total: number, pages: number}}> {
	return fetchJSON(`/news/search?q=${encodeURIComponent(q)}&page=${page}`);
}
export function getPopular(): Promise<{items: NewsCluster[], pagination: {page: number, per_page: number, total: number, pages: number}}> {
	return fetchJSON('/news/popular');
}
export function getCluster(id: number): Promise<NewsCluster & { source_items?: {source: string, title: string, url: string, snippet: string}[] }> {
	return fetchJSON(`/news/${id}`);
}
export function refreshNews(category: string, adminKey: string): Promise<{status: string}> {
	return fetchJSON('/admin/collect?category=' + category, {
		method: 'POST', headers: { 'X-Admin-Key': adminKey } as unknown as HeadersInit
	});
}
export function login(username: string, password: string): Promise<{access_token: string}> {
	return fetchJSON('/users/login', { method: 'POST', body: JSON.stringify({ username, password }) });
}
export function register(username: string, password: string): Promise<{access_token: string}> {
	return fetchJSON('/users/register', { method: 'POST', body: JSON.stringify({ username, password }) });
}
export function getFavorites(): Promise<NewsCluster[]> { return fetchJSON('/users/me/favorites'); }
export function toggleFavorite(clusterId: number): Promise<{favorited: boolean}> {
	return fetchJSON(`/users/me/favorites/${clusterId}`, { method: 'POST' });
}
