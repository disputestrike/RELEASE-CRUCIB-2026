/**
 * Prevents "ResizeObserver loop completed with undelivered notifications" by
 * deferring callbacks to the next animation frame. Must load before any code
 * that uses ResizeObserver (e.g. Sandpack, charts).
 */
if (typeof window !== "undefined" && window.ResizeObserver) {
  var NativeRO = window.ResizeObserver;
  window.ResizeObserver = function (callback) {
    return new NativeRO(function (entries, observer) {
      requestAnimationFrame(function () {
        callback(entries, observer);
      });
    });
  };
}
