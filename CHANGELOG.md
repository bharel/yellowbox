# Yellowbox Changelog
## 0.0.2: unreleased
### Added
* Short examples in the readme
* This changelog
* automatic testing in github repository
* the default package can now be used to import some common names.
* `KafkaService` can now accept the names of the zookeeper and broker images
* `connect` now accepts keyword arguments, forwarded to the inner connect call.
### Changed
* Project now uses poetry instead of setup.py
* `YellowKafka` has been renamed to `KafkaService`
* `YellowLogstash` has been renamed to `LogstashService`
* extra dependencies are now starred to increase compatibility.
### Fixed
* Bug where tests failed on linux because linux doesn't have `host.docker.internal`. Linux now uses IP `172.17.0.1` to target host.
* Bug where services would fail if trying to run a non-pulled image.
* Issue where the rabbit service test was not tries on the main tag.
* restored some network tests
* Bug in `connect` where networks would try to disconnect containers that have since been removed. 
* Bug in `KafkaService` where the service would try to kill if the containers even if they are no longer running.
* Bug in `KafkaService` where the network would not disconnect from the server after.

## 0.0.1: 17-8-2020
initial release