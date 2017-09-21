# Roll changelog

A changelog:

* is breaking-change-oriented
* links to related issues
* is concise

*Analogy: git blame :p*

## In progress

* Add documentation.

## 0.4.0 — 2017-09-21

* Switch routes from kua to autoroutes for performances.
* **Breaking change**:
  routes syntax change from `:parameter` to `{parameter}`

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
