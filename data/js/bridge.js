
(() => {

  Object.defineProperty(window, 'isIframe', {
    enumerable: true,
    configurable: true,
    get() {
      try {
        return window.self !== window.top;
      } catch (e) {
        return true;
      }
    }
  });
  document.addEventListener('DOMContentLoaded', (event) => {
    // Map all plugin registered objects to window

    if (!isIframe) {
      new QWebChannel(qt.webChannelTransport, (channel) => {
        let _channel = channel;
        let ev = new CustomEvent("ready");

        for (let key in _channel.objects) {
          console.log("adding plugin object", key)
          window[key] = _channel.objects[key];
        }
        document.dispatchEvent(ev);
      });
    }
  });


})();

