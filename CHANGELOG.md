# Changelog

## [0.1.7](https://github.com/anym001/ha-mos/compare/v0.1.6...v0.1.7) (2026-07-29)


### Features

* **api:** pace requests to stay under the server's rate limit ([acb6301](https://github.com/anym001/ha-mos/commit/acb63019363ee886d99111cd763705fd27f58023))
* **coordinator:** cap how long a failing resource may serve stale data ([065f386](https://github.com/anym001/ha-mos/commit/065f386e0b481a265b924202ff1ca341c767e487))
* **coordinator:** isolate communication errors per resource ([295040a](https://github.com/anym001/ha-mos/commit/295040a280404caa5b644bdbfeb289bd4a61c79f))
* **entity:** mark entities unavailable when their resource goes stale ([942c724](https://github.com/anym001/ha-mos/commit/942c72478c0b87e7aad9b51e64c57c3ae7ea4cf5))
* **manifest:** rename integration title to "MOS NAS" ([1f5a3f7](https://github.com/anym001/ha-mos/commit/1f5a3f7d5e76728c781a291923f333f2ef65c56d))
* pace API requests, isolate per-resource failures, and cap stale data ([77edb37](https://github.com/anym001/ha-mos/commit/77edb37143115d53a302ca41165afd423ac22d25))
* **sensor:** add hardware sensor readings from /sensors endpoint ([ff3800b](https://github.com/anym001/ha-mos/commit/ff3800b86980e78b06d40da0ee751c1f427e4803))
* **sensor:** add hardware sensor readings from /sensors endpoint ([2ed5e25](https://github.com/anym001/ha-mos/commit/2ed5e25dff104e1232cc0cc45c07b6b6dc27502b))
* **sensor:** add memory total/free/installed/reserved to system health ([9f18bc7](https://github.com/anym001/ha-mos/commit/9f18bc7a139c0e6b3617da28f40887fd8cbbd29d))


### Bug Fixes

* **config-flow:** clarify auth/connection error messages ([21efc59](https://github.com/anym001/ha-mos/commit/21efc5901a0d2a7e02c58e9f03b5b29b5a51b98c))
* **config-flow:** surface host in auth/connection error messages ([dc3cc2d](https://github.com/anym001/ha-mos/commit/dc3cc2d2fcf3543a3b2ac572300b0cbbb482a251))
* **coordinator:** drop MOS UI navigation path from a log message ([34c6d1a](https://github.com/anym001/ha-mos/commit/34c6d1a63d19547044a29f8ae7fca424b71c4596))
* **sensor:** correct device_class/state_class for hardware sensor subtypes ([b0f0817](https://github.com/anym001/ha-mos/commit/b0f081749268186e22564a2c413fc86faf7a5e2b))
* **sensor:** use stable id for hardware sensor identity, fix name quirks ([338e5dd](https://github.com/anym001/ha-mos/commit/338e5ddaa510088e4e2b10428ea906742e701961))
* **translations:** correct the documented minimum update interval ([33c296b](https://github.com/anym001/ha-mos/commit/33c296baef4aa82645fe869bb939909e46f627b6))
* **translations:** drop MOS UI navigation paths from user-facing strings ([d82b0c4](https://github.com/anym001/ha-mos/commit/d82b0c43f9a81221b5059a3d86f807d00cc257ac))

## [0.1.6](https://github.com/anym001/ha-mos/compare/v0.1.5...v0.1.6) (2026-07-28)


### Bug Fixes

* **coordinator:** retain last-known docker state on transient engine 403 ([1866d0f](https://github.com/anym001/ha-mos/commit/1866d0fd5cd0f0f2664f901ef7143f2f0008e644))
* **coordinator:** retain resources on transient 403/429 failures ([9c7720c](https://github.com/anym001/ha-mos/commit/9c7720c249ec92f50b2d0ad197f59ef179c27033))
* **coordinator:** stop Docker/LXC/VM entities disappearing on transient 403/429 ([723265a](https://github.com/anym001/ha-mos/commit/723265ac0150b54238ed7a0cd1e45db00cdf461f))

## [0.1.5](https://github.com/anym001/ha-mos/compare/v0.1.4...v0.1.5) (2026-07-28)


### Features

* **api:** request includeMetrics for /pools ([a5dc160](https://github.com/anym001/ha-mos/commit/a5dc160e91804321e2b32b416b595a18dc1bfc16))
* **api:** request performance and skipStandby params for /disks ([ffff325](https://github.com/anym001/ha-mos/commit/ffff3255ae38fbab12187d7f9441be111dbf8c15))
* **disks,pools:** expose type as its own sensor, not diagnostic ([2852667](https://github.com/anym001/ha-mos/commit/28526671255308c4cfa658e58bff93871820cc05))
* **disks:** add model and size sensors per disk ([827631b](https://github.com/anym001/ha-mos/commit/827631bb03360330442b164b91004e09fb0a8cc2))
* **entity:** give disks and pools their own device ([4036ff0](https://github.com/anym001/ha-mos/commit/4036ff038d714069fdcbbf16efbe80e0f1e73417))
* **pools:** add total/used space sensors and type attribute ([ae426d7](https://github.com/anym001/ha-mos/commit/ae426d7f5838eaef5d5e7650505c96c5ff3d77b7))
* **sensor,binary_sensor:** add disk temperature and preclear running sensors ([2dea2b8](https://github.com/anym001/ha-mos/commit/2dea2b81174cc27a115048d148fb4354a026efa8))


### Bug Fixes

* **disks:** remove the unverified temperature_status sensor ([175dcdc](https://github.com/anym001/ha-mos/commit/175dcdc52653f7714c74c8ba7a3acc46f69459e7))

## [0.1.4](https://github.com/anym001/ha-mos/compare/v0.1.3...v0.1.4) (2026-07-28)


### Bug Fixes

* **coordinator:** don't trigger reauth while the server is unavailable ([71ed432](https://github.com/anym001/ha-mos/commit/71ed432eae1a0b90b87b656546afbe8355aa5171))
* **coordinator:** keep the auth grace period across setup and reloads ([a7b352a](https://github.com/anym001/ha-mos/commit/a7b352a7e01acf64b48aee258c38ee27854d592a))
* **coordinator:** stop prompting for reauth when the token is not the problem ([aad4327](https://github.com/anym001/ha-mos/commit/aad4327578c16b2b6ef6f88ea3c2eb36d192b8cb))
* **coordinator:** stop treating a 403 as an invalid API token ([7ae18de](https://github.com/anym001/ha-mos/commit/7ae18debe2040f522224706bb3b40209369fec3d))


### Performance

* **coordinator:** raise minimum scan interval to 30s ([63e4348](https://github.com/anym001/ha-mos/commit/63e4348d97a09b5d0e3d28a4445cc642154d2ac1))

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
