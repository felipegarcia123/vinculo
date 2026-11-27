const DEFAULT_API_TIMEOUT_MS = 15_000;

/** @param {RequestInfo | URL} input @param {RequestInit} [init] @param {number} [timeoutMs] @param {typeof fetch} [fetchImplementation] */
export async function fetchWithTimeout(input, init = {}, timeoutMs = DEFAULT_API_TIMEOUT_MS, fetchImplementation = fetch) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetchImplementation(input, { ...init, signal: controller.signal });
  } catch (cause) {
    if (controller.signal.aborted) {
      throw new Error("El servicio tardó demasiado en responder. Intenta nuevamente.");
    }
    throw new Error("No fue posible conectar con el servicio. Comprueba tu conexión e intenta nuevamente.");
  } finally {
    clearTimeout(timer);
  }
}
