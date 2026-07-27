# Changelog

## [0.1.1](https://github.com/anym001/ha-mos/compare/v0.1.0...v0.1.1) (2026-07-27)


### Features

* **mos:** make the friendly name required ([cbf02c4](https://github.com/anym001/ha-mos/commit/cbf02c45032fc275fb3068ee5511fde62a57aa29))
* **mos:** optional friendly name as host-independent identity ([362ac49](https://github.com/anym001/ha-mos/commit/362ac49f2883f35c5114e85f57264fbb4b8f48f0))
* **mos:** read-only monitoring via /osinfo ([ac16b73](https://github.com/anym001/ha-mos/commit/ac16b73b39131cc54a5fc8f1bdb0088eb84f7194))
* **mos:** add pools, disks, and services entities, each pool/disk on its own device ([bf59e19](https://github.com/anym001/ha-mos/commit/bf59e19496ce2645fd57b7c8b342b49eacc41c68))


### Bug Fixes

* **docs:** apply Prettier formatting to README tables ([e1f540c](https://github.com/anym001/ha-mos/commit/e1f540c5a2ab6e03b38c7c8857a8ad6977b826ab))
* **mos:** coerce config-entry port to int to prevent float-corrupted URLs, and remove the entity registry entry when a disk/pool disappears, not just its state ([28c2688](https://github.com/anym001/ha-mos/commit/28c2688e2a98562f9766d266acd8320dfa544541))


### Tests

* add pytest suite for config flow, coordinator, API client, and entities ([28c2688](https://github.com/anym001/ha-mos/commit/28c2688e2a98562f9766d266acd8320dfa544541))


### CI/CD

* run the test suite on every push/PR to main and dev ([6382f06](https://github.com/anym001/ha-mos/commit/6382f064b4bda60ade3bb1fc03c559b27134dc66))
