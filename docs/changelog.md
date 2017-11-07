# Roll changelog

A changelog:

* is breaking-change-oriented
* links to related issues
* is concise

*Analogy: git blame :p*

## dev version

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
* **Breaking changes**:
    * `options` extension is no more applied by default
      ([#16](https://github.com/pyrates/roll/pull/16))
    * deprecated `req` pytest fixture is now removed
      ([#9](https://github.com/pyrates/roll/pull/9))

## 0.5.0 — 2017-09-21

* Add documentation.
* Move project to Github.
* **Breaking change**:
  order of parameters in events is always `request`, `response` and
  optionnaly `error` if any, in that particular order.

## 0.4.0 — 2017-09-21

* Switch routes from kua to autoroutes for performances.
* **Breaking change**:
  routes placeholder syntax changed from `:parameter` to `{parameter}`

## 0.3.0 — 2017-09-21

* Improve benchmarks and overall performances.
* **Breaking change**:
  `cors` extension parameter is no longer `value` but `origin`

## 0.2.0 — 2017-08-25

* Resolve HTTP status only at response write time.

## 0.1.1 — 2017-08-25

* Fix `setup.py`.

## 0.1.0 — 2017-08-25

* First release
