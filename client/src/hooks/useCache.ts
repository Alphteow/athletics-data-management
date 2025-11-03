import { useState, useEffect, useRef } from 'react';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiry: number;
}

export function useCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttl: number = 5 * 60 * 1000 // 5 minutes default
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cacheRef = useRef<Map<string, CacheEntry<T>>>(new Map());

  useEffect(() => {
    const fetchData = async () => {
      const cached = cacheRef.current.get(key);
      const now = Date.now();

      // Return cached data if it exists and hasn't expired
      if (cached && now < cached.expiry) {
        setData(cached.data);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const freshData = await fetcher();
        const entry: CacheEntry<T> = {
          data: freshData,
          timestamp: now,
          expiry: now + ttl
        };
        
        cacheRef.current.set(key, entry);
        setData(freshData);
      } catch (err: any) {
        setError(err.message || 'Failed to fetch data');
        // Return cached data even if expired if fetch fails
        if (cached) {
          setData(cached.data);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [key, ttl]);

  const invalidate = () => {
    cacheRef.current.delete(key);
    setData(null);
  };

  const refresh = async () => {
    cacheRef.current.delete(key);
    setLoading(true);
    setError(null);

    try {
      const freshData = await fetcher();
      const entry: CacheEntry<T> = {
        data: freshData,
        timestamp: Date.now(),
        expiry: Date.now() + ttl
      };
      
      cacheRef.current.set(key, entry);
      setData(freshData);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, invalidate, refresh };
}
