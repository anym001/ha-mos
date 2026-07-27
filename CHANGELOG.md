# Changelog

## [0.1.3](https://github.com/anym001/ha-mos/compare/v0.1.2...v0.1.3) (2026-07-27)


### Bug Fixes

* **api:** raise Docker/LXC start/stop timeout to avoid false stop failures ([#28](https://github.com/anym001/ha-mos/issues/28)) ([5cd7ca4](https://github.com/anym001/ha-mos/commit/5cd7ca46bc984ac78900965b6b3977f2883f11f2))
* **deps:** remove stale dev target-branch from dependabot config ([#29](https://github.com/anym001/ha-mos/issues/29)) ([6b72b06](https://github.com/anym001/ha-mos/commit/6b72b06e2ea27b0846987310678c56e010d96759))

## [0.1.2](https://github.com/anym001/ha-mos/compare/v0.1.1...v0.1.2) (2026-07-27)


### Features

* add LXC/Docker container and VM entities with power switches ([c1c5124](https://github.com/anym001/ha-mos/commit/c1c5124262d211138f72078a6f45a50ff573c3e5))
* **mos:** add brand dark icon assets ([5bd573e](https://github.com/anym001/ha-mos/commit/5bd573e0388b771d29936368fed4cc7e10d3baba))
* **mos:** add brand icon assets ([2c8ca85](https://github.com/anym001/ha-mos/commit/2c8ca85234280abe353b5ca43f151e7d6116123c))
* **mos:** add brand icon assets ([8c56030](https://github.com/anym001/ha-mos/commit/8c56030b2bf2d102695e5e692c86749ce04e884d))
* **mos:** introspect token permission scope once at coordinator setup ([9be6f5c](https://github.com/anym001/ha-mos/commit/9be6f5c9a9685bb83c4f10559c34436403e426cd))
* **mos:** introspect token permission scope once at coordinator setup ([130969a](https://github.com/anym001/ha-mos/commit/130969ade36ddcf5fe8a4e6154f5db4fbd43d89e))
* **sensor,binary_sensor:** add LXC and Docker container entities ([164f289](https://github.com/anym001/ha-mos/commit/164f289f9e79105529dd70d8776c27581969c7ea))
* **sensor:** add live system health sensors ([cbfaeb7](https://github.com/anym001/ha-mos/commit/cbfaeb73cde7ff4d189e12c911537df96c01a502))
* **sensor:** add live system health sensors ([bb24629](https://github.com/anym001/ha-mos/commit/bb24629883d96daf2e449783da659bfa85e99e95))
* **switch:** add Docker container power switch, gate writes on token permissions ([37037b7](https://github.com/anym001/ha-mos/commit/37037b7a18d7ee6fceaddecde463e89ad708b1cf))
* **vm:** add per-VM devices with CPU/memory sensors, autostart, and power switch ([814a717](https://github.com/anym001/ha-mos/commit/814a717a12bf07be71cd3f7cb7645b2e2ec408d6))

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
