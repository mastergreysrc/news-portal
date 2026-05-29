import { writable } from 'svelte/store';

function storedWritable<T>(key: string, initial: T) {
	const stored = typeof localStorage !== 'undefined' ? localStorage.getItem(key) : null;
	const store = writable<T>(stored !== null ? JSON.parse(stored) : initial);
	if (typeof localStorage !== 'undefined') {
		store.subscribe(v => {
			if (v === null || v === undefined || v === '') {
				localStorage.removeItem(key);
			} else {
				localStorage.setItem(key, typeof v === 'string' ? v : JSON.stringify(v));
			}
		});
	}
	return store;
}

export const token = storedWritable<string | null>('token', null);
export const adminKey = storedWritable<string>('adminKey', '');
