# Hatch Node Build

[![PyPI - Version](https://img.shields.io/pypi/v/hatch_node_build.svg)](https://pypi.org/project/hatch_node_build)

A plugin for [Hatch](https://github.com/pypa/hatch) that allows you to run Node.js builds and include the build
artifacts in your Python package.

## Installation

To set up `hatch-node-build`, set `hatchling` as your build backend, and add `hatch-node-build` as a
dependency, and as a Hatch build hook:

```toml
[build-system]
requires = ["hatchling", "hatch-build-scripts"]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.node-build]
```

Including simply the table header as shown here is valid minimal TOML to enable the hook. Additional
configuration of the plugin is added here as well.

## Usage

The plugin allows you to build a JavaScript bundle with `npm run build` (by default, see configuration). Simply
include your Node assets in a folder called `/browser`, and it will be included in your Python package.

A minimal [React](https://react.dev/) app using [`esbuild`](https://esbuild.github.io/) would look as follows:

```
/
├─ my_python_module/
│  └─ __init__.py
└─ browser/
   ├─ src/
   │  └─ index.jsx
   └─ package.json
```

### `browser/package.json`

```json
{
  "name": "my-react-esbuild-app",
  "version": "1.0.0",
  "description": "A minimal React app using ESBuild",
  "type": "module",
  "scripts": {
    "build": "esbuild src/index.jsx --bundle --outfile=dist/bundle.js --format=iife --minify",
    "watch": "esbuild src/index.jsx --bundle --outfile=dist/bundle.js --format=iife --sourcemap --watch"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "esbuild": "^0.18.0"
  }
}
```

### `browser/src/index.jsx`

```js
import React from 'react';
import ReactDOM from 'react-dom/client';

const App = () => {
  return <h1>Hello, React with ESBuild in a Python package!</h1>;
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
```

After the build, the Python package would include `bundle/app.js`. See [Runtime](#runtime) for more information on
different ways to launch your JavaScript bundle when a user uses your package.

## Build & build configuration

The default build uses the `/browser` directory in your repository as the source directory, and bundles the output
(from the `/browser/dist` directory) in the output distribution in the `bundle` directory.

The steps of a build are as follows:

* Check `/browser/package.json` for Node.js requirements.
* Use Node.js found on PATH
  * If no matching version is found, install LTS version in cache.
* Run `npm install` in `/browser`
* Run `npm run build` in `/browser`
* Include `/browser/dist` in output as `/bundle`

The build can be configured in the following ways:

| Key               | Default           | Description                                                                           |
|-------------------|-------------------|---------------------------------------------------------------------------------------|
| `node_executable` | `"node"`          | Path to node executable to use.                                                       |
| `lts`             | `True`            | Only install LTS versions.                                                            |
| `install_command` | `"npm install"`   | The command to run to initialize the Node environment.                                |
| `build_command`   | `"npm run build"` | The command to run to build the artifacts.                                            |
| `source_dir`      | `"browser"`       | The location where the JavaScript source assets are stored.                           |
| `artifact_dir`    | `"dist"`          | The location relative to the source directory where the build artifacts end up.       |
| `bundle_dir`      | `"bundle"`        | The location in the Python package output the bundle should be included at.           |
| `inline_bundle`   | `False`           | Inline the JavaScript bundle `{artifact_dir}/bundle.js` in `{source_dir}/index.html`. |

If you need to make changes to the configuration, specify them in the build hook configuration:

```toml
[tool.hatch.build.hooks.node-build]
source_dir = "src/web"
bundle_dir = "web"
```

## Runtime

Using `hatch-node-build` you can include the bundle in your package, but that doesn't open the app yet when someone
uses your package.

There are a few things to consider, for example, the user's target machine might not have the Node.js runtime available,
so `hatch-node-build` works best, and focuses on frontend application bundles to be run in the browser.

Most web bundlers create bundles that span multiple files/chunks so that the web app can be loaded incrementally for
faster load times, and the bundle has to be served from an HTTP server. Spawning and controlling an HTTP server from
Python create challenging restrictions on the architecture of your code. It can be a lot simpler for small
applications to inline the JavaScript bundle in an HTML file and have the user's platform open it for you.

### Inlining the bundle

`hatch-node-build` supports simple inlining of your built bundle if the `inline_bundle` setting is turned on. It will look
for a file called `index.html` in the source directory, and will replace the script tag that points to `{artifact_dir}/bundle.js`.

For example:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>Sample React App</title>
  </head>
  <body>
    <div id="root"></div>
    <script src="dist/bundle.js"></script>
  </body>
</html>

```

Your Python package will then include `bundle/index.html` instead of `bundle/bundle.js`, and you can simply:

```python
import pathlib
import webbrowser

webbrowser.open(pathlib.Path(__file__).parent / "bundle" / "index.html")
```

Your code will not block and simply continue its execution.

### Running through an HTTP server

This is a simple example for an HTTP server. The Python process will be blocked while serving the HTTP server,
so you'll likely want a better and event-loop or async-based solution:

```python
import http.server
import socketserver
import os

PORT = 8000
web_dir = os.path.join(os.path.dirname(__file__), "static")
os.chdir(web_dir)

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving at http://localhost:{PORT}")
    httpd.serve_forever()
```

