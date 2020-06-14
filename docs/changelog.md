# Roll changelog

A changelog:

* is breaking-change-oriented
* links to related issues
* is concise

*Analogy: git blame :p*

## 0.12.0 - 2020-06-14

- Added `app.url_for` helper ([#136](https://github.com/pyrates/roll/pull/136))
- Added `response.redirect` shortcut ([#134](https://github.com/pyrates/roll/pull/134))
- Fixed URL not quoted in testing utility
- Added `default_index` to `static` extension ([#95](https://github.com/pyrates/roll/pull/95))
- Added support for streamed responses ([#89](https://github.com/pyrates/roll/pull/89))
- Added support for async reading of request body ([#89](https://github.com/pyrates/roll/pull/89))
- `Request.json` is now cached ([#90](https://github.com/pyrates/roll/pull/90))

## 0.11.0 - 2019-05-07

- **Breaking change**:
    * Removed python 3.5 support ([#81](https://github.com/pyrates/roll/pull/81))
- Added support for class-based views ([#80](https://github.com/pyrates/roll/pull/80))
- Added support for chunked response ([#81](https://github.com/pyrates/roll/pull/81))

## 0.10.0 - 2018-11-08

- python 3.7 compatibility (bump websockets and biscuits packages)
  ([#69](https://github.com/pyrates/roll/pull/69))
- uvloop is not a dependency anymore (but you should still use it!): need was
  to allow installing Roll without uvloop is some envs, and to let the users
  define the uvloop version they want to use
  ([#68](https://github.com/pyrates/roll/pull/68))
- `Request.method` is `None` by default ([#67](https://github.com/pyrates/roll/pull/67))
- allow to use `methods=*` in `cors` extension
  ([#65](https://github.com/pyrates/roll/pull/65))

## 0.9.1 - 2018-06-11

* Do not try to write on a closed transport
  ([#58](https://github.com/pyrates/roll/pull/58))

## 0.9.0 - 2018-06-04

* **Breaking changes**:
    * `Request.route` is now always set, but `Request.route.payload` is `None`
      when path is not found. This allows to catch a not found request in the
      `request` hook. Note: if the `request` hook does not return a response,
      a 404 is still automatically raised.
      ([#45](https://github.com/pyrates/roll/pull/45))
* Added `request.host` shortcut ([#43](https://github.com/pyrates/roll/pull/43))
* Introduced protocol upgrade and protocol configuration for routes. Two
  protocols are shipped by default : HTTP and Websocket
  ([#54](https://github.com/pyrates/roll/pull/54)).
* The route is now resolved as soon as the URL has been parsed. In addition, the
  route lookup method has been split up from the application `__call__`method,
  to allow easy override
  ([#54](https://github.com/pyrates/roll/pull/54)).
* Testing: now build a proper request instead of calling callbacks by hand
  ([#54](https://github.com/pyrates/roll/pull/54)).


## 0.8.0 - 2017-12-11

* **Breaking changes**:
    * `Request` and `Response` classes now take `app` as init parameter. It
      allows lazy parsing of the query while keeping the `Query` class reference
      on `Roll` application.
      ([#35](https://github.com/pyrates/roll/pull/35))
* Added support for request body parsing through multifruits
  ([#38](https://github.com/pyrates/roll/pull/38))


## 0.7.0 - 2017-11-27

* **Breaking changes**:
    * `Query`, `Request` and `Response` are not anymore attached to the
      `Protocol` class. They are now declared at the `Roll` class level.
      It allows easier subclassing and customization of these parts.
      ([#30](https://github.com/pyrates/roll/pull/30))
    * Removed Request.kwargs in favor of inheriting from dict, to store user
      data in a separate space
      ([#33](https://github.com/pyrates/roll/pull/33))
    * Request headers are now normalized in upper case, to work around
      inconsistent casing in clients
      ([#24](https://github.com/pyrates/roll/pull/24))
* Only set the body and Content-Length header when necessary
  ([#31](https://github.com/pyrates/roll/pull/31))
* Added `cookies` support ([#28](https://github.com/pyrates/roll/pull/28))


## 0.6.0 — 2017-11-22

* **Breaking changes**:
    * `options` extension is no more applied by default
      ([#16](https://github.com/pyrates/roll/pull/16))
    * deprecated `req` pytest fixture is now removed
      ([#9](https://github.com/pyrates/roll/pull/9))
* Changed `Roll.hook` signature to also accept kwargs
  ([#5](https://github.com/pyrates/roll/pull/5))
* `json` shorcut sets `utf-8` charset in `Content-Type` header
  ([#13](https://github.com/pyrates/roll/pull/13))
* Added `static` extension to serve static files for development
  ([#16](https://github.com/pyrates/roll/pull/16))
* `cors` accepts `headers` parameter to control `Access-Control-Allow-Headers`
  ([#12](https://github.com/pyrates/roll/pull/12))
* Added `content_negociation` extension to reject unacceptable client requests
  based on the `Accept` header
  ([#21](https://github.com/pyrates/roll/pull/21))
* Allow to set multiple `Set-Cookie` headers
  ([#23](https://github.com/pyrates/roll/pull/23))

## 0.5.0 — 2017-09-21

* **Breaking change**:
  order of parameters in events is always `request`, `response` and
  optionnaly `error` if any, in that particular order.
* Add documentation.
* Move project to Github.

## 0.4.0 — 2017-09-21

* **Breaking change**:
  routes placeholder syntax changed from `:parameter` to `{parameter}`
* Switch routes from kua to autoroutes for performances.

## 0.3.0 — 2017-09-21

* **Breaking change**:
  `cors` extension parameter is no longer `value` but `origin`
* Improve benchmarks and overall performances.

## 0.2.0 — 2017-08-25

* Resolve HTTP status only at response write time.

## 0.1.1 — 2017-08-25

* Fix `setup.py`.

## 0.1.0 — 2017-08-25

* First release
