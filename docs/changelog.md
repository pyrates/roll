# Roll changelog

A changelog:

* is breaking-change-oriented
* links to related issues
* is concise

*Analogy: git blame :p*

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
