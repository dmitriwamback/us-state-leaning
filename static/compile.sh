em++ main.cpp -o main.mjs \
  -s MODULARIZE=1 -s EXPORT_ES6=1 \
  -s MIN_WEBGL_VERSION=2 -s MAX_WEBGL_VERSION=2 \
  -s USE_WEBGL2=1 -s FULL_ES3=1 \
  -s EXPORTED_FUNCTIONS=_setState,_setViewportSize,_main \
  -s EXPORTED_RUNTIME_METHODS=ccall,cwrap \
  --preload-file state-models@state-models \
  -lGL