import { useEffect, useRef, useState } from "react";

/** Exécute `fn` immédiatement puis toutes les `ms` millisecondes. */
export default function usePolling(fn, ms) {
  const [state, setState] = useState({ data: null, error: null, at: null });
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const data = await fnRef.current();
        if (alive) setState({ data, error: null, at: Date.now() });
      } catch (error) {
        if (alive) setState((s) => ({ ...s, error }));
      }
    };
    tick();
    const id = setInterval(tick, ms);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [ms]);

  return state;
}
