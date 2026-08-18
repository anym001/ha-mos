# Changelog

## [0.2.3](https://github.com/anym001/ha-mos/compare/v0.2.2...v0.2.3) (2026-08-18)


### Bug Fixes

* **deps:** stop pinning tooling Home Assistant already installs ([78408b5](https://github.com/anym001/ha-mos/commit/78408b55758bd44114802d9da8a4c14aafe5e915))
* **hassfest:** activate the venv before detecting the HA version ([f4f00cf](https://github.com/anym001/ha-mos/commit/f4f00cfec8a44ee38544526f578e7133dbb582bf))
* **sensor:** normalize hardware reading units to HA's spelling ([7b4d284](https://github.com/anym001/ha-mos/commit/7b4d2841df72207ecf111eb0d76e75879c26d04a))

## [0.2.2](https://github.com/anym001/ha-mos/compare/v0.2.1...v0.2.2) (2026-08-17)


### Features

* **api:** reach the endpoints and files behind guest icons ([429d93e](https://github.com/anym001/ha-mos/commit/429d93eabaa8a991cd19430bf362c602f4effc10))
* **coordinator:** resolve the icons MOS serves for its own guests ([51329c1](https://github.com/anym001/ha-mos/commit/51329c130eaf489f64eed526fab85da1381e3b97))
* **entity:** mark container devices with a machine-readable model_id ([26cad36](https://github.com/anym001/ha-mos/commit/26cad36c56df509db64b4fccc1b147f0e652a109))
* **entity:** show the server-hosted icon on LXC and VM sensors ([bf99e68](https://github.com/anym001/ha-mos/commit/bf99e68557586e102343eb276dad621b692ceb21))
* **sensor:** translate the disk power status ([bd92912](https://github.com/anym001/ha-mos/commit/bd92912758b618f14ecc29170e52aa908e8dead9))


### Bug Fixes

* **coordinator:** give up on guest icon endpoints that cannot answer ([d6b58ae](https://github.com/anym001/ha-mos/commit/d6b58aeeb075ad179d244df3ee0fcdb7567ef998))
* **diagnostics:** redact guest icon URLs alongside web links ([6243008](https://github.com/anym001/ha-mos/commit/6243008a04b5898d2f122d28055054b3993ccc54))

## [0.2.1](https://github.com/anym001/ha-mos/compare/v0.2.0...v0.2.1) (2026-08-14)


### Features

* **api:** add the Docker container stats endpoint ([23d97d5](https://github.com/anym001/ha-mos/commit/23d97d5227a615957e2dbe70ee888f9c2b772998))
* **api:** add the per-container Docker template endpoint ([f5780ac](https://github.com/anym001/ha-mos/commit/f5780ac824392077e0dfa9d22fa3c5acb504e0a5))
* **coordinator:** collect per-container Docker stats ([a67ee63](https://github.com/anym001/ha-mos/commit/a67ee63b15195e07a3a2c98b98d3f0622118571e))
* **coordinator:** harvest engine fields and cache Docker templates ([9264b04](https://github.com/anym001/ha-mos/commit/9264b04987ff5af2ce980873ef57aea9a20353fc))
* **entity:** expose Docker container state, health and web link ([c0bba46](https://github.com/anym001/ha-mos/commit/c0bba463189ae9cf7cdaf3d074d0e9f72531b1da))
* **entity:** expose Docker CPU and memory sensors ([1bf3a31](https://github.com/anym001/ha-mos/commit/1bf3a316c1daac39fca65de8d56c758110cb99e9))
* **entity:** expose LXC container and VM state as a sensor ([94d8d70](https://github.com/anym001/ha-mos/commit/94d8d70a23d9d1c4eddb69a83cdaf714a2701c9a))


### Bug Fixes

* **diagnostics:** keep bind addresses and labels out of the dump ([6f021a1](https://github.com/anym001/ha-mos/commit/6f021a1374ef01ef268fdc1d3063c714a96c8d16))

## [0.2.0](https://github.com/anym001/ha-mos/compare/v0.1.10...v0.2.0) (2026-08-11)


### ⚠ BREAKING CHANGES

* **deps:** Home Assistant 2026.4 through 2026.7 are no longer supported. The device registry APIs this release adopts do not exist before 2026.8, and HACS will stop offering updates on older cores.

### Features

* **deps:** require Home Assistant 2026.8 ([cf78c4a](https://github.com/anym001/ha-mos/commit/cf78c4a5a8e6a8e29c5f6f7b2b567a18940e2c15))


### Bug Fixes

* **hassfest:** activate the venv before detecting the HA version ([03ffecd](https://github.com/anym001/ha-mos/commit/03ffecdc953226b6de9d80be5ad9b0c3777bf7ee))
* **setup:** pick the venv this environment actually maintains ([4d4bcb0](https://github.com/anym001/ha-mos/commit/4d4bcb0bac33163e5366c4256f741f5a3b80a51d))
* **setup:** rebuild the venv before installing into it ([f274f6d](https://github.com/anym001/ha-mos/commit/f274f6db74d80f2480151da47ac4326cbfbb1d55))

## [0.1.10](https://github.com/anym001/ha-mos/compare/v0.1.9...v0.1.10) (2026-08-05)


### Features

* **binary-sensor:** add a sensor for every NUT status flag ([1767aa2](https://github.com/anym001/ha-mos/commit/1767aa254db75166a9f6f8d2cb1f0bda88e5df53))
* **binary-sensor:** add state-dependent icons for in-progress sensors ([420eab5](https://github.com/anym001/ha-mos/commit/420eab540a21c68c2037345710d56f6dbc9b3246))
* **diagnostics:** report the device name override and area ([3df0dc5](https://github.com/anym001/ha-mos/commit/3df0dc5f4d98d8a6a0022104990352af29889617))
* **entity:** group UPS sensors under their own device ([afdc6c9](https://github.com/anym001/ha-mos/commit/afdc6c9fe68179862d6b7e3bb27bdbaff9a6fcb6))
* **entity:** let container devices follow the server's area ([749799d](https://github.com/anym001/ha-mos/commit/749799d65b6e05edd70dda26a62179b541f08a08))


### Bug Fixes

* **api:** tell a rejected token apart from a denied resource ([aa1c134](https://github.com/anym001/ha-mos/commit/aa1c134997a20453c428f7858afab2dedcb58e4c))
* **binary-sensor:** file the UPS calibration run as diagnostic ([a217421](https://github.com/anym001/ha-mos/commit/a217421aee7a3e8cdbe47fa07ae38973d5b4b880))
* **binary-sensor:** show the UPS discharge flag as primary ([ba48108](https://github.com/anym001/ha-mos/commit/ba48108487cbbb4285e3006245a99e23dd27a73f))
* **coordinator:** stop re-asking for a resource the server refused ([10c332e](https://github.com/anym001/ha-mos/commit/10c332e48727375557b6a3fe2ca64cbbc37c6b48))
* **entity:** keep the container device info type-checked ([a888118](https://github.com/anym001/ha-mos/commit/a8881182025f7ebf92ffa92f04129a54f9a11776))
* **entity:** name the UPS's own maker on its device page ([6e09f96](https://github.com/anym001/ha-mos/commit/6e09f966d37341985d112d61693bd194944bd3e0))
* **sensor:** clean up misleading and colliding UPS icons ([0ce304d](https://github.com/anym001/ha-mos/commit/0ce304db9eba818a98105e09d32180de6d049244))
* **sensor:** file the UPS nameplate sensors as diagnostic ([6f63e6c](https://github.com/anym001/ha-mos/commit/6f63e6c4867197783d32701949930aa477ea71a9))
* **tests:** count the UPS device in the diagnostics device total ([a5765ec](https://github.com/anym001/ha-mos/commit/a5765ec7e584efdd12d206697f6e53863e65bf49))
* **translations:** correct the German name of the HB flag ([0d6f56a](https://github.com/anym001/ha-mos/commit/0d6f56a10203e3ac088dbad0abe8c5fd955a3c10))

## [0.1.9](https://github.com/anym001/ha-mos/compare/v0.1.8...v0.1.9) (2026-08-03)


### Features

* **api:** add UPS entities from the nut/status endpoint ([e356cef](https://github.com/anym001/ha-mos/commit/e356cef010ba995ee6c70f80e2e8121f0d393f68))
* **api:** report missing endpoints as unsupported instead of failures ([fab7625](https://github.com/anym001/ha-mos/commit/fab762518c944b7b0262446fa1e713bede04c8ba))
* **coordinator:** map the UPS resource to the nut token scope ([0a4dd45](https://github.com/anym001/ha-mos/commit/0a4dd4507731024a43774f95c903e2b54d0f160f))
* **coordinator:** warn once when MOS cannot read its UPS ([63f7193](https://github.com/anym001/ha-mos/commit/63f71937fabd446cbb9904983f1b9077e148ce60))
* **entity:** create UPS entities only once a UPS answers ([01cc076](https://github.com/anym001/ha-mos/commit/01cc0764349dc08ad6d9df727ae2d5a84b08e083))
* **translations:** describe the connection fields in both languages ([8b2a452](https://github.com/anym001/ha-mos/commit/8b2a4527502898290d728f28b846dcebd99e8dfc))


### Bug Fixes

* **api:** url-encode container and vm names in request paths ([290fc86](https://github.com/anym001/ha-mos/commit/290fc86c162d3f2743984cc76a5200896aa3f560))
* **coordinator:** map services to the mos scope, not a made-up one ([6f71bee](https://github.com/anym001/ha-mos/commit/6f71bee6bff4ee1c6f76874819dd200415067d88))
* **coordinator:** name the MOS permission resource in denial messages ([9c7100b](https://github.com/anym001/ha-mos/commit/9c7100be165295f1dcda26bae926aa75e2b60e7f))
* **diagnostics:** include the hardware sensor readings ([59c30a4](https://github.com/anym001/ha-mos/commit/59c30a45d7252b49764a466fca0d514355e725fb))
* **diagnostics:** redact host and hardware identifiers from dumps ([c95c708](https://github.com/anym001/ha-mos/commit/c95c7080bee365786461b64604e03394eee417ee))

## [0.1.8](https://github.com/anym001/ha-mos/compare/v0.1.7...v0.1.8) (2026-07-30)


### Features

* **ci:** enforce conventional commits with a commitlint hook ([0557160](https://github.com/anym001/ha-mos/commit/0557160977770c9f8eefe912e091271261a7ab5b))
* **logging:** improve diagnostics and error visibility ([ac68746](https://github.com/anym001/ha-mos/commit/ac68746450db8f16f6877f381c37daab85155376))
* **sensor:** add average CPU core temperature ([3cd366d](https://github.com/anym001/ha-mos/commit/3cd366d67bcdd5d1d32438c3d3f03c45dfc353cf))
* **sensor:** add swap, RAM breakdown and max CPU temperature ([758e0c6](https://github.com/anym001/ha-mos/commit/758e0c6cf49dc2febdc7fb4007a8d8efcb3b8a15))
* **translations:** add German translation ([e9392b0](https://github.com/anym001/ha-mos/commit/e9392b0bb9203fc8dec6e0d6ebe1f20346b5df2a))


### Bug Fixes

* **ci:** spell-check AGENTS.md, CLAUDE.md and docs/ ([8a15188](https://github.com/anym001/ha-mos/commit/8a151887b7980cd3530068b7ad91cbac34d0d8ed))
* **ci:** stop commitlint enforcing undocumented line-length rules ([db8d1db](https://github.com/anym001/ha-mos/commit/db8d1db9efe3ce496559161bfe6b1728669e71c5))
* **deps:** declare pre-commit and fail bootstrap when hooks are missing ([8b9fc43](https://github.com/anym001/ha-mos/commit/8b9fc4369b8c8963a8791be8a46a58a82b301ddb))
* **translations:** use masculine article for Token in de.json ([a8e1919](https://github.com/anym001/ha-mos/commit/a8e1919a6899839003b0c6cd417a7d786f025d8c))

## [0.1.7](https://github.com/anym001/ha-mos/compare/v0.1.6...v0.1.7) (2026-07-29)


### Features

* **api:** pace requests to stay under the server's rate limit ([acb6301](https://github.com/anym001/ha-mos/commit/acb63019363ee886d99111cd763705fd27f58023))
* **coordinator:** cap how long a failing resource may serve stale data ([065f386](https://github.com/anym001/ha-mos/commit/065f386e0b481a265b924202ff1ca341c767e487))
* **coordinator:** isolate communication errors per resource ([295040a](https://github.com/anym001/ha-mos/commit/295040a280404caa5b644bdbfeb289bd4a61c79f))
* **entity:** mark entities unavailable when their resource goes stale ([942c724](https://github.com/anym001/ha-mos/commit/942c72478c0b87e7aad9b51e64c57c3ae7ea4cf5))
* **manifest:** rename integration title to "MOS NAS" ([1f5a3f7](https://github.com/anym001/ha-mos/commit/1f5a3f7d5e76728c781a291923f333f2ef65c56d))
* **sensor:** add hardware sensor readings from /sensors endpoint ([2ed5e25](https://github.com/anym001/ha-mos/commit/2ed5e25dff104e1232cc0cc45c07b6b6dc27502b))
* **sensor:** add memory total/free/installed/reserved to system health ([9f18bc7](https://github.com/anym001/ha-mos/commit/9f18bc7a139c0e6b3617da28f40887fd8cbbd29d))


### Bug Fixes

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

* **mos:** add brand dark icon assets ([5bd573e](https://github.com/anym001/ha-mos/commit/5bd573e0388b771d29936368fed4cc7e10d3baba))
* **mos:** add brand icon assets ([8c56030](https://github.com/anym001/ha-mos/commit/8c56030b2bf2d102695e5e692c86749ce04e884d))
* **mos:** introspect token permission scope once at coordinator setup ([130969a](https://github.com/anym001/ha-mos/commit/130969ade36ddcf5fe8a4e6154f5db4fbd43d89e))
* **sensor,binary_sensor:** add LXC and Docker container entities ([164f289](https://github.com/anym001/ha-mos/commit/164f289f9e79105529dd70d8776c27581969c7ea))
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
