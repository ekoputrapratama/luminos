/**
 * A modified version of THREE.LoadingManager and THREE.ImageLoader
 * that will work in iframe context and use async api.
 *
 */

function LuminosLoadingManager(onLoad, onProgress, onError) {

  var scope = this;

  var isLoading = false;
  var itemsLoaded = 0;
  var itemsTotal = 0;
  var urlModifier = undefined;

  // Refer to #5689 for the reason why we don't set .onStart
  // in the constructor

  this.onStart = undefined;
  this.onLoad = onLoad;
  this.onProgress = onProgress;
  this.onError = onError;

  this.itemStart = function (url) {

    itemsTotal++;

    if (isLoading === false) {

      if (scope.onStart !== undefined) {

        scope.onStart(url, itemsLoaded, itemsTotal);

      }

    }

    isLoading = true;

  };

  this.itemEnd = function (url) {

    itemsLoaded++;

    if (scope.onProgress !== undefined) {

      scope.onProgress(url, itemsLoaded, itemsTotal);

    }

    if (itemsLoaded === itemsTotal) {

      isLoading = false;

      if (scope.onLoad !== undefined) {

        scope.onLoad();

      }

    }

  };

  this.itemError = function (url) {

    if (scope.onError !== undefined) {

      scope.onError(url);

    }

  };

  this.resolveURL = function (url) {

    if (urlModifier) {

      return urlModifier(url);

    }

    return url;

  };

  this.setURLModifier = function (transform) {

    urlModifier = transform;
    return this;

  };

}

var DefaultLuminosLoadingManager = new LuminosLoadingManager();

function LuminosImageLoader(manager) {
  this.manager = (manager !== undefined) ? manager : DefaultLuminosLoadingManager;
}

Object.assign(LuminosImageLoader.prototype, {
  crossOrigin: 'anonymous',
  load: function (url, onLoad, onProgress, onError) {

    if (url === undefined) url = '';

    if (this.path !== undefined) url = this.path + url;


    url = this.manager.resolveURL(url);
    var scope = this;

    var image = document.createElementNS('http://www.w3.org/1999/xhtml', 'img');

    function onImageLoad() {

      image.removeEventListener('load', onImageLoad, false);
      image.removeEventListener('error', onImageError, false);

      if (onLoad) onLoad(this);

      scope.manager.itemEnd(url);

    }

    function onImageError(event) {

      image.removeEventListener('load', onImageLoad, false);
      image.removeEventListener('error', onImageError, false);

      if (onError) onError(event);

      scope.manager.itemError(url);
      scope.manager.itemEnd(url);

    }

    image.addEventListener('load', onImageLoad, false);
    image.addEventListener('error', onImageError, false);

    if (url.substr(0, 5) !== 'data:') {
      if (this.crossOrigin !== undefined) image.crossOrigin = this.crossOrigin;
    }

    scope.manager.itemStart(url);
    return LuminosFetch(url).then(str => {
      image.src = str;
      return image;
    });
  },

  setCrossOrigin: function (value) {
    this.crossOrigin = value;
    return this;
  },

  setPath: function (value) {
    this.path = value;
    return this;
  }
});
