# Change Log

## [1.1.0](https://github.com/NASA-AMMOS/AIT-DSN/tree/1.1.0) (2019-10-10)
[Full Changelog](https://github.com/NASA-AMMOS/AIT-DSN/compare/1.1.0_alpha...1.1.0)

**Closed issues:**

- Default SLE config parameters should be functional / provide sane defaults [\#77](https://github.com/NASA-AMMOS/AIT-DSN/issues/77)
- Hostname / Port configuration options [\#76](https://github.com/NASA-AMMOS/AIT-DSN/issues/76)
- Transfer frame instantiation in RAF [\#74](https://github.com/NASA-AMMOS/AIT-DSN/issues/74)
- Add communication through sockets to CFDP implementation [\#73](https://github.com/NASA-AMMOS/AIT-DSN/issues/73)
- Add SLE docs [\#71](https://github.com/NASA-AMMOS/AIT-DSN/issues/71)
- Remove unused configuration files [\#67](https://github.com/NASA-AMMOS/AIT-DSN/issues/67)
- Add method for saving encoded CLTU to file [\#66](https://github.com/NASA-AMMOS/AIT-DSN/issues/66)
- Specify multiple DSN hostnames; connect to active one [\#64](https://github.com/NASA-AMMOS/AIT-DSN/issues/64)
- RCF status report invocation handler is not generating report properly [\#63](https://github.com/NASA-AMMOS/AIT-DSN/issues/63)
- RAF/RCF start/end times should accept null values per spec [\#62](https://github.com/NASA-AMMOS/AIT-DSN/issues/62)
- Common SLE class socket close bug [\#61](https://github.com/NASA-AMMOS/AIT-DSN/issues/61)
- Document and run current CFDP implementation  [\#58](https://github.com/NASA-AMMOS/AIT-DSN/issues/58)
- CFDP Class 2 Implementation [\#52](https://github.com/NASA-AMMOS/AIT-DSN/issues/52)
- Move RAF/RCF/CLTU handlers into SLE base class [\#7](https://github.com/NASA-AMMOS/AIT-DSN/issues/7)

**Merged pull requests:**

- Issue \#64 - Attempt SLE connection to multiple hostnames [\#86](https://github.com/NASA-AMMOS/AIT-DSN/pull/86) ([aywaldron](https://github.com/aywaldron))
- Issue 76 - add option to pull hostname / port from config [\#83](https://github.com/NASA-AMMOS/AIT-DSN/pull/83) ([Futabay](https://github.com/Futabay))
- Issue \#77 - Update SLE config parameters [\#82](https://github.com/NASA-AMMOS/AIT-DSN/pull/82) ([Futabay](https://github.com/Futabay))
- Issue \#73 - CFDP send/receive over UDP socket connection [\#81](https://github.com/NASA-AMMOS/AIT-DSN/pull/81) ([aywaldron](https://github.com/aywaldron))
- Issue \#71 - Add SLE documentation [\#80](https://github.com/NASA-AMMOS/AIT-DSN/pull/80) ([aywaldron](https://github.com/aywaldron))
- Fix issue \#74 [\#75](https://github.com/NASA-AMMOS/AIT-DSN/pull/75) ([kmarwah](https://github.com/kmarwah))
- Issue \#58 - CFDP documentation [\#72](https://github.com/NASA-AMMOS/AIT-DSN/pull/72) ([aywaldron](https://github.com/aywaldron))
- Issue \#66 - Add save-to-file method to CLTU [\#70](https://github.com/NASA-AMMOS/AIT-DSN/pull/70) ([aywaldron](https://github.com/aywaldron))
- Issue \#67 - Remove unused SLE transfer frame definition yamls [\#68](https://github.com/NASA-AMMOS/AIT-DSN/pull/68) ([aywaldron](https://github.com/aywaldron))
- Bugfixes [\#55](https://github.com/NASA-AMMOS/AIT-DSN/pull/55) ([FabianBurger](https://github.com/FabianBurger))

## [1.1.0_alpha](https://github.com/NASA-AMMOS/AIT-DSN/tree/1.1.0_alpha) (2019-03-14)
[Full Changelog](https://github.com/NASA-AMMOS/AIT-DSN/compare/1.0.0...1.1.0_alpha)

**Closed issues:**

- Class 2 Receiver NAK procedures [\#48](https://github.com/NASA-AMMOS/AIT-DSN/issues/48)
- Push DSN build to PyPi [\#12](https://github.com/NASA-AMMOS/AIT-DSN/issues/12)

**Merged pull requests:**

- CFDP Class 2 NAK procedures [\#53](https://github.com/NASA-AMMOS/AIT-DSN/pull/53) ([lorsposto](https://github.com/lorsposto))
- Issue 83 in AIT-CORE: Baseline example configs across repos [\#51](https://github.com/NASA-AMMOS/AIT-DSN/pull/51) ([aywaldron](https://github.com/aywaldron))

## [1.0.0](https://github.com/NASA-AMMOS/AIT-DSN/tree/1.0.0) (2018-07-10)
**Closed issues:**

- Convert README to rst and update setup.py in preparation for PyPi publishing [\#43](https://github.com/NASA-AMMOS/AIT-DSN/issues/43)
- Credential handling is missing proper microsecond handling [\#40](https://github.com/NASA-AMMOS/AIT-DSN/issues/40)
- Update FCLTU to for differences between v4 and v5 [\#39](https://github.com/NASA-AMMOS/AIT-DSN/issues/39)
- Add build status badge to README [\#36](https://github.com/NASA-AMMOS/AIT-DSN/issues/36)
- TravisCI build breaking [\#34](https://github.com/NASA-AMMOS/AIT-DSN/issues/34)
- Update README with default contributing and community information [\#32](https://github.com/NASA-AMMOS/AIT-DSN/issues/32)
- Drop documentation upgrade scripts now that ReadTheDocs builds are up [\#29](https://github.com/NASA-AMMOS/AIT-DSN/issues/29)
- TM Transfer Frame Header Parsing is incorrect [\#24](https://github.com/NASA-AMMOS/AIT-DSN/issues/24)
- Update rcf\_api\_test for version 4 tests [\#23](https://github.com/NASA-AMMOS/AIT-DSN/issues/23)
- Update tm\_downlink\_example for version 4 tests [\#22](https://github.com/NASA-AMMOS/AIT-DSN/issues/22)
- Default CFDP config paths point to invalid directory structure [\#21](https://github.com/NASA-AMMOS/AIT-DSN/issues/21)
- Tests break on clean checkout of repo [\#20](https://github.com/NASA-AMMOS/AIT-DSN/issues/20)
- Setup TravisCI build [\#19](https://github.com/NASA-AMMOS/AIT-DSN/issues/19)
- Add docs build badge to README [\#17](https://github.com/NASA-AMMOS/AIT-DSN/issues/17)
- Add CODEOWNERS file [\#15](https://github.com/NASA-AMMOS/AIT-DSN/issues/15)
- Get DSN docs built and publicly viewable [\#13](https://github.com/NASA-AMMOS/AIT-DSN/issues/13)
- Update SLE specific references to broader "DSN" naming [\#11](https://github.com/NASA-AMMOS/AIT-DSN/issues/11)
- Switch AIT-DSN BLISS naming over to AIT [\#10](https://github.com/NASA-AMMOS/AIT-DSN/issues/10)
- Publish docs to ReadTheDocs [\#8](https://github.com/NASA-AMMOS/AIT-DSN/issues/8)
- Implement BIND-level auth for SLE [\#5](https://github.com/NASA-AMMOS/AIT-DSN/issues/5)
- Update README [\#3](https://github.com/NASA-AMMOS/AIT-DSN/issues/3)
- Requires bliss-core 0.23.0 [\#2](https://github.com/NASA-AMMOS/AIT-DSN/issues/2)

**Merged pull requests:**

- Issue \#43 - Convert README.md to .rst and update setup.py in prep for PyPi release [\#44](https://github.com/NASA-AMMOS/AIT-DSN/pull/44) ([lorsposto](https://github.com/lorsposto))
- Issue \#40 - Fix credential microsecond handling [\#42](https://github.com/NASA-AMMOS/AIT-DSN/pull/42) ([MJJoyce](https://github.com/MJJoyce))
- Issue \#39 Update FCLTU for V4 and V5 [\#41](https://github.com/NASA-AMMOS/AIT-DSN/pull/41) ([lorsposto](https://github.com/lorsposto))
- Issue \#10 and \#11 - Renaming updates [\#38](https://github.com/NASA-AMMOS/AIT-DSN/pull/38) ([MJJoyce](https://github.com/MJJoyce))
- Issue \#36 - Add build status badge to README [\#37](https://github.com/NASA-AMMOS/AIT-DSN/pull/37) ([MJJoyce](https://github.com/MJJoyce))
- Issue \#34 - Fix broken TravisCI build [\#35](https://github.com/NASA-AMMOS/AIT-DSN/pull/35) ([MJJoyce](https://github.com/MJJoyce))
- Issue \#32 - Update README with contributing and community info [\#33](https://github.com/NASA-AMMOS/AIT-DSN/pull/33) ([MJJoyce](https://github.com/MJJoyce))
- Issue \#19 - Add TravisCI config file [\#31](https://github.com/NASA-AMMOS/AIT-DSN/pull/31) ([MJJoyce](https://github.com/MJJoyce))
- Issue \#29 - Remove doc upgrade script [\#30](https://github.com/NASA-AMMOS/AIT-DSN/pull/30) ([lorsposto](https://github.com/lorsposto))
- Issue \#21 - Update CFDP config paths and check in directories [\#28](https://github.com/NASA-AMMOS/AIT-DSN/pull/28) ([lorsposto](https://github.com/lorsposto))
- Issue \#24 - Fix TMFrame header bit mask issues [\#27](https://github.com/NASA-AMMOS/AIT-DSN/pull/27) ([MJJoyce](https://github.com/MJJoyce))
- Issue \#23 - Update RCF example for version 4 support [\#26](https://github.com/NASA-AMMOS/AIT-DSN/pull/26) ([MJJoyce](https://github.com/MJJoyce))
- Issue \#22 - RAF example changes for version 4 support [\#25](https://github.com/NASA-AMMOS/AIT-DSN/pull/25) ([MJJoyce](https://github.com/MJJoyce))
- Issue \#17 - Add docs build badge to README [\#18](https://github.com/NASA-AMMOS/AIT-DSN/pull/18) ([MJJoyce](https://github.com/MJJoyce))
- Issue \#15 - Add CODEOWNERS file [\#16](https://github.com/NASA-AMMOS/AIT-DSN/pull/16) ([MJJoyce](https://github.com/MJJoyce))
- Issue \#2 - Bump ait-core version and remove outdated dependency link [\#14](https://github.com/NASA-AMMOS/AIT-DSN/pull/14) ([MJJoyce](https://github.com/MJJoyce))
- Issue \#8 - Publish docs to ReadTheDocs [\#9](https://github.com/NASA-AMMOS/AIT-DSN/pull/9) ([lorsposto](https://github.com/lorsposto))
- Issue \#5 - Implement BIND-level authentication [\#6](https://github.com/NASA-AMMOS/AIT-DSN/pull/6) ([lorsposto](https://github.com/lorsposto))
- Issue \#3 - Update README [\#4](https://github.com/NASA-AMMOS/AIT-DSN/pull/4) ([lorsposto](https://github.com/lorsposto))
- Issue \#12 Testing + corresponding code fixes [\#1](https://github.com/NASA-AMMOS/AIT-DSN/pull/1) ([lorsposto](https://github.com/lorsposto))



\* *This Change Log was automatically generated by [github_changelog_generator](https://github.com/skywinder/Github-Changelog-Generator)*