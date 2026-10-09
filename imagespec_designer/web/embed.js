/**
 * Mount one isolated designer instance in a host page.
 * Each iframe owns its state and DOM, so one host can mount multiple editors.
 * The passed host may provide profile, messages, api/apiBase, render,
 * loadDocument, and saveDocument callbacks. See the package README.
 */
export async function mount(root, host = {}) {
  if (!(root instanceof Element))
    throw new TypeError("mount root must be an Element");
  const base = new URL("./", import.meta.url);
  const response = await fetch(new URL("index.html", base));
  if (!response.ok)
    throw new Error(`Could not load designer UI (${response.status})`);
  let html = await response.text();
  html = html.replace(/<script[^>]*src="\/designer\.js"[^>]*><\/script>/i, "");
  html = html.replace("<head>", `<head><base href="${base.href}">`);
  const frame = document.createElement("iframe");
  frame.title = host.title || "imagespec designer";
  frame.style.cssText =
    "width:100%;height:100%;min-height:500px;border:0;display:block";
  root.replaceChildren(frame);
  await new Promise((resolve, reject) => {
    frame.addEventListener("load", resolve, { once: true });
    frame.addEventListener("error", reject, { once: true });
    frame.src = "about:blank";
  });
  const doc = frame.contentDocument;
  doc.open();
  doc.write(html);
  doc.close();
  let resolveReady, rejectReady;
  const ready = new Promise((resolve, reject) => {
    resolveReady = resolve;
    rejectReady = reject;
  });
  const suppliedReady = host.onReady,
    suppliedError = host.onError;
  frame.contentWindow.imageSpecDesignerHost = {
    ...host,
    onReady() {
      suppliedReady?.();
      resolveReady();
    },
    onError(error) {
      suppliedError?.(error);
      rejectReady(error);
    },
  };
  const module = doc.createElement("script");
  module.type = "module";
  module.src = new URL("designer.js", base).href;
  doc.body.append(module);
  module.onerror = () =>
    rejectReady(new Error("Could not load the designer module"));
  try {
    await Promise.race([
      ready,
      new Promise((_, reject) =>
        setTimeout(
          () => reject(new Error("Designer startup timed out")),
          15000,
        ),
      ),
    ]);
  } catch (error) {
    frame.remove();
    throw error;
  }
  return {
    frame,
    ready: Promise.resolve(),
    getDocument() {
      return frame.contentWindow.imagespecDesigner.getDocument();
    },
    setDocument(value) {
      return frame.contentWindow.imagespecDesigner.setDocument(value);
    },
    refresh() {
      return frame.contentWindow.imagespecDesigner.refresh();
    },
    validate(value) {
      return frame.contentWindow.imagespecDesigner.validate(value);
    },
    unmount() {
      frame.remove();
    },
  };
}
