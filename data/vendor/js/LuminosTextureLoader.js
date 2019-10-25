/**
 * A modified version of THREE.TextureLoader
 * that will work in iframe context and use async api.
 *
 */


function LuminosTextureLoader(manager) {

  this.manager = (manager !== undefined) ? manager : DefaultLuminosLoadingManager;

}

Object.assign(LuminosTextureLoader.prototype, {

  crossOrigin: 'anonymous',

  load: function (url, onLoad, onProgress, onError) {

    var texture = new THREE.Texture();

    var loader = new LuminosImageLoader(this.manager);
    loader.setCrossOrigin(this.crossOrigin);
    loader.setPath(this.path || url);

    return loader.load('', null, onProgress, onError).then(image => {
      texture.image = image;

      // JPEGs can't have an alpha channel, so memory can be saved by storing them as RGB.
      var isJPEG = url.search(/\.jpe?g($|\?)/i) > 0 || url.search(/^data\:image\/jpeg/) === 0;

      texture.format = isJPEG ? THREE.RGBFormat : THREE.RGBAFormat;
      texture.needsUpdate = true;

      if (onLoad !== undefined) {
        onLoad(texture);
      }
      return texture;
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

