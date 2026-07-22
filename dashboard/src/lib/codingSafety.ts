/** Shared coding-challenge validators (safe for API + browser imports). */

export const ENTRYPOINT_RE = /^[A-Za-z_][A-Za-z0-9_]{0,64}$/;
export const MAX_SOURCE_BYTES = 32_768;

/**
 * Conservative denylist for *structural* feedback only.
 * Not a sandbox — server grading must never execute user source.
 */
export const DANGEROUS_SOURCE =
  /\b(require|process|globalThis|global|Function|eval|import|export|child_process|fs|net|http|https|vm|worker_threads|worker_thread|WebAssembly|Reflect|Proxy|constructor|__proto__|module\.exports|Buffer|setImmediate|setInterval|setTimeout|getBuiltinModule)\b|["']constru["']\s*\+|["']pro["']\s*\+|[\u2028\u2029]|\\u00/i;

export function assertSafeEntrypoint(entrypoint: string): string | null {
  if (!ENTRYPOINT_RE.test(entrypoint)) {
    return "Entrypoint must be a simple identifier";
  }
  return null;
}

export function assertSafeSource(source: string): string | null {
  if (!source || !source.trim()) return "Empty submission";
  if (typeof Buffer !== "undefined") {
    if (Buffer.byteLength(source, "utf8") > MAX_SOURCE_BYTES) {
      return "Source exceeds size limit";
    }
  } else if (source.length > MAX_SOURCE_BYTES) {
    return "Source exceeds size limit";
  }
  if (DANGEROUS_SOURCE.test(source)) {
    return "Source uses disallowed APIs";
  }
  return null;
}
