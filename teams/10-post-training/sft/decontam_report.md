# SFT decontamination report

Run for G10 on 2026-11-06 to 2026-11-09. Every set was checked against Team 9's benchmark fingerprints **v2** with the **full set** (no `--benchmarks`, `--tags` or `--exclude`), and scanned for canaries.

- **set_sha256:** `2826a3b883210c653979103c09ce1c79e40fc4f7034b54027f2836482370d22a`
- **Tools:** `teams/09-evaluation/decontam/decontam_check.py` and `canary_scan.py`, lab main `c6b0ce0961028020b3e3eaf86fe0c5873fca3bc0`. sha256 of the files used:
  - `canary_scan.py`: `322066d675e13af8bee0d05602f755f49e33da5a148bf664306ce6d6a9f908c2`
  - `decontam_check.py`: `62a269a25123543b5470c4956ba1be530ea257c597bc2be2eab19201cb62df8f`
  - `fpset.py`: `7f5f48d08506d619ebfadd2742e86d29ec3ea28e5fcfd729f13cd8d959689c59`
  - `lab_canary.py`: `373536a777c9f16367cf6affcc2cc6243755ac23e75850a2624eadf65918ea09`
  - `normalize.py`: `570dcb820ac2ae6c667b1abc5ea1d781a6795aa42a7735aa94377e756d7d70e9`
- **Runner and reconciliation:** `sft/decontam_run.py`; this file is written by `sft/decontam_report.py`.
- **Sets run:** 34. **Rows in:** 17,438,781. **Removed (flagged or canary):** 460,409 (2.64%). **Kept:** 16,978,372.
- No benchmark item text is in this file or in the run records: only set names, counts, document ids, benchmark item ids, offsets and sha256 values.

## 1. Result per set

| Set | Run on | Rows in | Flagged | Canary | Removed | Rows kept | Clean file sha256 |
|---|---|---:|---:|---:|---:|---:|---|
| `sft-agentic-nemotron-agentic-v1` | full set | 315,560 | 432 | 0 | 432 (0.14%) | 315,128 | `5f05e6f91fbe…` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | full set | 364,889 | 2,146 | 0 | 2,146 (0.59%) | 362,743 | `b67d3a7e1be4…`, `c08822705eda…`, `22a2f622cb9a…`, `0a25e39d3340…`, `b4ecf0815a4f…`, `053e6ba68c58…`, `0ee5176f74ea…`, `b448e52cf403…`, `93aa60bd3752…`, `d1eba6b18db8…`, `3ac1eff32010…`, `5590c5450663…`, `f00baef059e5…`, `62bf5adbbd09…`, `7c0fe76205f9…`, `486fb688253b…`, `4ea06d2ceddc…`, `d3a9e7b468d1…`, `2da74c01c873…`, `17ffc3edc1b6…`, `4529a5362e3e…`, `42692681da71…`, `8db16ceac7d5…`, `36487f0b971a…`, `b3de6d0991a3…` |
| `sft-bespoke-stratos-17k` | full set | 16,710 | 1,791 | 0 | 1,791 (10.72%) | 14,919 | `7ba1dc2bb254…` |
| `sft-chat-nemotron-if-v1` | full set | 4,963 | 1 | 0 | 1 (0.02%) | 4,962 | `38e757a1a7f8…` |
| `sft-chat-nemotron-if-v2` | full set | 929,130 | 5,820 | 0 | 5,820 (0.63%) | 923,310 | `d275e5fc036a…`, `129921cf9708…`, `fa59bf8e5412…`, `7cfc5eac47ec…`, `9f434f177f06…`, `84b302f24bc3…`, `1de7ab5945bf…`, `95ee581fa4b7…`, `8786b14b2153…`, `2db777df7567…`, `dfe1154ba357…`, `8ee148c1f184…`, `2f9ddc83eca2…`, `ca5c6a4d63bd…`, `58fc17fa19c0…`, `ae4ba4a2e852…`, `a6440d349208…`, `528a1c30fcf2…`, `d5b1a0a38e99…`, `4ab4d078274d…`, `2201fd1dca64…`, `5a792d0c4f3b…`, `a8a7284e9979…`, `da409765b5e0…`, `dd1c17be5e1e…`, `5fde6e9c38f1…`, `a17c0ff681ce…`, `624b556ba607…`, `64edd9dd9c9f…`, `c67e1d319c41…`, `e9ac4479954e…`, `b17bd1527fd8…`, `b0ac423bf558…`, `2de5563c2e80…` |
| `sft-code-codeforces-cots` | full set | 45,734 | 20,796 | 0 | 20,796 (45.47%) | 24,938 | `b5df0cfbc19b…` |
| `sft-code-commitpackft` | full set | 56,025 | 15 | 0 | 15 (0.03%) | 56,010 | `e34bda519e71…` |
| `sft-code-nemotron-cascade-swe` | full set | 210,582 | 18,248 | 0 | 18,248 (8.67%) | 192,334 | `ec7e6a4e58e8…`, `b9aaf1093062…`, `f1524e849126…`, `b7e3ebb5dc8f…`, `c4700d5da8c7…`, `91de7b00189f…`, `058cccb5229b…`, `3f56e742de15…`, `0fca44d358a8…`, `0b501560491e…`, `7d1e2ef8c7bf…`, `f82da2a04c2f…`, `7618789a1f73…`, `94b8ed89df74…`, `020a4a1c7882…`, `acc3d8f4ef93…`, `f98976abc534…`, `21f6b684fa80…`, `dfac7970bfa9…`, `ff3c3bcbc331…`, `dad9eca584aa…`, `d7c97dad7b3a…`, `356f34dfb865…`, `6bb300fb1545…` |
| `sft-code-nemotron-cuda` | full set | 2,273 | 2 | 0 | 2 (0.09%) | 2,271 | `f451b673db79…` |
| `sft-code-nemotron-opencode` | full set | 67,086 | 332 | 0 | 332 (0.49%) | 66,754 | `dc562d0cc443…`, `3576800758a9…`, `52b89bc87e69…`, `203bfab03d84…`, `79c4877ed535…`, `f51db030cd1b…`, `1b83bfbd73c4…`, `c2dbcd0e59fa…`, `908d315b0121…`, `c74074761b8b…`, `0ae8c0e47d8e…`, `6c1b81f80ad8…`, `97de60f12503…`, `44dea49aa7e2…`, `319e3bec33bd…`, `eecfa70e05a2…`, `ae13045008f6…`, `7b9ae04c4554…`, `90944e688cf0…`, `e9afa04e9c57…`, `ef96eb70bb11…` |
| `sft-code-nemotron-terminal` | full set | 31,928 | 9,901 | 0 | 9,901 (31.01%) | 22,027 | `59278bca72a9…` |
| `sft-code-opencodereasoning` | full set | 567,831 | 112,753 | 0 | 112,753 (19.86%) | 455,078 | `6cbda38e7041…`, `6649b96a6d1c…`, `e47ae9eef7ba…`, `cc55d55aed99…`, `8617985dd2fc…`, `206a80c2ea60…`, `77a7aa9e3030…`, `ab3186f3d36d…`, `6d48fc84bcaf…`, `b6d952120b40…`, `d5f7ea4f1e79…`, `ae1d958b8345…`, `261cfe87985b…`, `9cb52f31f6d5…`, `1b648ddf84fb…`, `72bbb73bf80a…`, `f5ef1be6327e…`, `9d317faedd42…`, `230de697e342…`, `9957957f69b4…`, `27f5797cb00c…`, `e6d63201e69c…`, `453833144bb0…`, `2450161c2948…`, `84e031af054b…`, `3570616e5664…`, `a71405aacf84…`, `630c1c72a0b7…`, `97d64d94325e…`, `7da7db9e6764…`, `5d12d0449a5a…`, `84616c6b65b5…`, `29cefacd0840…`, `1ffd3300e08c…`, `55726df6a17e…`, `1af02cc4882c…`, `0627106dadcc…`, `e22bf8937afc…`, `5978b3c80490…`, `4d5e6a04c323…`, `b3e7cbdda302…`, `3cf268dc0c22…`, `76f0219e3d4d…`, `06b563083508…`, `a9271b57778c…`, `0173b4d26e00…`, `5547374f35af…`, `51a0017a3e11…`, `5a3c2752b787…`, `87bd128d197d…`, `072eec7b0c9e…`, `3a6d9190f470…`, `9c448e424aec…`, `7b723d227bb2…`, `5a5722ee61f0…`, `320a48325003…`, `4a0e637eca75…`, `005db673df8b…`, `9bcffa0ff01e…`, `a35b7ae99304…`, `d8e53ff01022…`, `693421bb13c0…`, `b77316e1aa6c…`, `ced0d14f6e58…`, `a43a36d5603b…`, `27aac9a62f34…`, `a78b0d30a5d3…`, `573b2e8aa4a7…`, `2a86104df132…`, `891a3b6dd635…`, `43e78e2ac6ba…`, `51f128ae0e2a…`, `dee827f24f32…`, `c07ca437384f…`, `a44e07451a5b…` |
| `sft-code-opencodereasoning-2` | all 70 python shards, questions joined | 542,219 | 115,067 | 0 | 115,067 (21.22%) | 427,152 | — |
| `sft-code-swe-rebench-openhands` | full set | 27,516 | 4,864 | 0 | 4,864 (17.68%) | 22,652 | `7c2b95c36dc0…` |
| `sft-code-swe-zero-openhands` | full set | 317,039 | 22,167 | 0 | 22,167 (6.99%) | 294,872 | `edcee5f6a064…`, `3988bc112a21…`, `369e0425a5dc…`, `ce4d83831cd5…`, `7b2e0a66f36c…`, `453a9a99b878…`, `20e65f2945c2…`, `56c5db671015…`, `d8b51f7f7c1e…`, `2cd5b06a10db…`, `09cb9d40d401…`, `8ede36e3b753…`, `71aaa26ba5bc…`, `e454cfaf4eda…`, `5f10455a35b8…`, `a76f4f1940be…`, `62e2aee444e9…`, `80d3e65146c1…`, `4dfa1e17e0bf…`, `c582bb5e9e2c…`, `35f570d3e389…`, `e6a264589840…`, `fe72b1e7976b…`, `482e1d85265b…`, `96dc4695d2c0…`, `301b0f1d32be…`, `aba62328301d…`, `e8f5fdd23d65…`, `a734d5222a17…`, `bfa9979767a2…`, `111f0d57f0d5…`, `09678231fe30…`, `d4ae0f7850a5…`, `84236c603aaf…`, `35f6b53a2c47…`, `a9e53f0620d6…`, `ca6483ab3cdf…`, `334d76403d86…`, `20ba94f0feb5…`, `d55ea0cf20b5…`, `7077c501b060…`, `59216d0373c3…`, `a31b60f9f057…`, `d5397f87e7f1…`, `618612ec5cb0…`, `6370c661988c…`, `b114b2f7b82f…`, `f1509f6400ad…`, `b47e7b6fd81f…`, `7da236e1c33e…`, `0f541e5dc421…`, `ccadab0a94c3…`, `edada892bc4b…`, `eace8098b643…`, `a4698e5c14a1…`, `eef4a12a42d5…`, `7dcaa2d6b8d1…`, `ac6e46a35d9b…`, `5ebad7ee254b…`, `68b4674ebf00…`, `f7f577dd2b26…`, `1c7140b3488a…`, `f72e436a25b6…`, `dbfc70f0bfb2…`, `17adef40fe86…`, `d3e43f90f8a7…`, `9c08beecd8fe…`, `24333b26ab62…`, `97c2ce7383e3…`, `97458d468e40…`, `4e7745952aad…`, `9d29e3a1b0f8…`, `655fb8c4ef41…`, `735ebe311d2d…`, `9415d384bc81…`, `367ec27efb30…`, `ff161c02e469…`, `668b12aa9a66…`, `ee693bfe563d…`, `cb264c679a47…`, `1776195baf12…`, `c64cc90e9ac4…`, `7850da597c08…`, `52d7b7cc1878…`, `788158c1e0c9…`, `edf1aa166ffa…`, `6d446a80ec37…`, `2ad36b778d1c…`, `6b3e3fe76635…`, `db3f8cebbe9e…`, `ff3672f29529…`, `a5f74e66eceb…`, `e7409a022ac4…`, `e0933c7bde79…`, `3b28ceedf8a7…`, `e2bb5d850415…`, `0f36f26e6ba3…`, `485a5812f4e4…`, `e2bbccdd4101…`, `b6545d17a77a…`, `0de385661863…`, `19bee8bc1a35…`, `5ac9f007915b…`, `954886aa8dbb…`, `92d6903ab073…`, `92119e4c2744…`, `f29bf7273d54…`, `b70d8d5dfacd…`, `ff5c446fa2d1…`, `ebb3e07613ad…`, `186b9a13f4e3…`, `f0691ef3f020…`, `5f2f0c4c0fc3…`, `899ad739cffa…`, `9cb21263fa93…`, `92224f4f2ff0…`, `d028c09995b8…`, `bd3273e35e5d…`, `6565792be46d…`, `3fdf362182d9…`, `976e1c69f96d…`, `5e61eb131deb…`, `16df6caedcfa…`, `1c9f23acc5dc…`, `e7e12bac9b14…`, `a13d972c8de1…`, `171ef9b0732b…`, `a627743038b7…`, `8730fc48449b…`, `e35540bf6497…`, `e42f82509334…`, `5cc14a4748ee…`, `b30cf2df1c8c…`, `f49428587f14…`, `bbb6ff6852fd…`, `6f470e3c953f…`, `16399627cb5d…` |
| `sft-dolly-15k` | full set | 15,011 | 4 | 0 | 4 (0.03%) | 15,007 | `93069f7a3a2c…` |
| `sft-indic-aya-collection` | full set | 654,530 | 6 | 0 | 6 (0.00%) | 654,524 | `cb4b80d9253a…` |
| `sft-indic-aya-dataset` | full set | 41,261 | 8 | 0 | 8 (0.02%) | 41,253 | `a1d2c8f07122…` |
| `sft-indic-indic-align-dolly-t` | full set | 10,541 | 0 | 0 | 0 (0.00%) | 10,541 | `3af21a7c294c…` |
| `sft-indic-indic-align-oasst-t` | full set | 19,909 | 9 | 0 | 9 (0.05%) | 19,900 | `219d0a5fcb3c…` |
| `sft-math-nemotron-math-v2` | full set | 7,079,896 | 60,665 | 0 | 60,665 (0.86%) | 7,019,231 | `27c65cac950e…`, `f19b10b9d206…`, `84e1ddcb3def…`, `6a957902a3a4…`, `10d3918d7c30…`, `f585f501e3d6…`, `fed5fe3fa8e5…`, `a8b090f46bab…`, `49133eb89ec0…`, `65d80fefa97e…`, `4a7b8aa4d16f…`, `522201078ae1…`, `b4feaebe4742…`, `1d957aca4f7d…`, `5f07ec5b5b31…`, `17f1bcb8d232…`, `dc33b0613b07…`, `f15a012d93d4…`, `8f5ebb8ea566…`, `2f1ab4423cea…`, `802a50b9e4eb…`, `849481e57408…`, `7f4e7d84a2d1…`, `4446e824a5dd…`, `63658a614a0d…`, `92ec346667da…`, `65ce89e71ceb…`, `d42d704c3c3e…`, `d2c7e56ea7e6…`, `d1252729f69b…`, `6f0683ce1633…`, `7c260fd3c33c…`, `6f29a9ee0b26…`, `85ba981f3363…`, `f314229d4d5e…`, `3f5d25fe8cda…`, `af5c3a5621da…`, `b03820fda2ab…`, `b1bf8a343aec…`, `68186e1aae2d…`, `482e17c7a49d…`, `c59580a1a47a…`, `12a575bc883f…`, `306798c60d31…`, `f17208f0a10d…`, `f9211fb7f101…`, `2ffa0c31740c…`, `bde4a48f05de…`, `4cf9472d34f0…`, `24a192b3f7cc…`, `413962c30845…`, `cf67025ee601…`, `8522b3b249ed…`, `6fb93be82b43…`, `b34a7737d816…`, `4f4184890d61…`, `91897e613729…`, `0e9148d086e6…`, `9237011e0819…`, `4f5a6e13c605…`, `19499a2da095…`, `1a0cc5a057b7…`, `fa2852bc0169…`, `33293c78381d…`, `78d875859a33…`, `bac430d5d08d…`, `ed0774060ab2…`, `81f0766a92f9…`, `e13c6501fb4c…`, `8bb42a2a57cf…`, `dbaee3b8d085…`, `5936ec5e3f91…`, `649297836036…`, `9809fb830a3a…`, `cc2e1f47379e…`, `b7c899679cf6…`, `ceca4bbcfea8…`, `781072b80c8c…`, `fcd9e6ea5a1c…`, `914a508ea4b2…`, `0d0bef9aecdd…`, `de8ca4c029f0…`, `c21c809bf274…`, `003746006cb4…`, `b4af14c08162…`, `b2fb07b7cede…`, `890c11ead088…`, `49a66538a51e…`, `8f6fc125866a…`, `bd3b500640a5…`, `b427ddcde93e…`, `4cd4b01d2f39…`, `fb7f1c24a5c9…`, `a021b726107d…`, `2fda528c8e42…`, `34be18f48761…`, `17d0c727344c…`, `2a120e261795…`, `62f689c673e3…`, `72889b66102a…`, `6d536631e234…`, `a234ce89912b…`, `bfc25d2ecc46…`, `242af4a05ea8…`, `6a2c06667807…`, `d444728f24c7…`, `b2e38ddeff09…`, `9129eb87ca30…`, `ddbfcae672bc…`, `297d9b0b7441…`, `19f822e66bb4…`, `e2262d7b899c…`, `c9475138dd01…`, `a0619b5bc059…`, `2a383ba67dff…`, `7d0a97975c0e…`, `f59526a71b4d…`, `6e187410eb65…`, `54a1e2785d3b…`, `5697ab18e5b3…`, `c4620e46ffaf…`, `8c767892c298…`, `a75d94307968…`, `ca53b78ed919…`, `6cc7eed6b59b…`, `73b9e9da033e…`, `e2aca007ec85…`, `5ef31c363c10…`, `da9b1d9ddd1c…`, `1f1c689ce1d0…`, `8173ee3dd79d…`, `6bd159fe144c…`, `4ca1bad936e4…`, `023ef17d3bcf…`, `ec34ddf7bc52…`, `fae813aae341…`, `95011762a9d7…`, `870677dc03f3…`, `ca9258d85599…`, `a7e116d2c3a3…`, `a51e45ff4a65…`, `8d221cf43d78…`, `5eaf39d8b158…`, `99d22e4af60a…`, `4ef10fa8f5ed…`, `054f1424243f…`, `d6512f9d8c3a…`, `2924aba43448…`, `edbc3b574b9c…`, `0d93375576e9…`, `582f7b7b9e4f…`, `675afa91298c…`, `3273429e3e16…`, `4b7e6722156f…`, `2079d22b9e80…`, `0a299bbd742b…`, `70ea508e1231…`, `9dfdc10bdeb0…`, `c3b89577fb5b…`, `01b83e3faf7f…`, `4d1da1390d5f…`, `6d32b2b66a57…`, `825c9f9e2c3e…`, `53015c296114…`, `14315ffbef05…`, `6d6aea6ddf2c…`, `4065610efd48…`, `3fab004702a4…`, `c18421aca1a3…`, `e9f2df097147…`, `68299fa54052…`, `65d87bd522d0…`, `d9d4b63dddb8…`, `29cb25560380…`, `51aa4d51d11b…`, `52b11b397824…`, `268ea247c196…`, `64b76d7eca7c…`, `f5606d18aeef…`, `6d3440e3c823…`, `2b4c3c493e86…`, `e98900cdf426…`, `b39e7c74bb02…`, `46f12d6ec567…`, `51c30586f0fb…`, `497a751ea3cf…`, `f18177d0b5c9…`, `19db1eabee7a…`, `b552fa1e1599…`, `8161f6caaca9…`, `ddb0708f912b…`, `2d083d7d89e4…`, `3c45379036ed…`, `6e0e0c9cfde1…`, `b9e89de76759…`, `61b318527c99…`, `2581646d8cd9…`, `520e59ed7325…`, `57476bc1356f…`, `1ab843e4e046…`, `9da9807c0aa2…`, `0b4e8e8f5104…`, `4bec9074bb99…`, `543e4c97b4b6…`, `1e11b229ee37…`, `8e6b8dd04fe9…`, `3fa3476da098…`, `5096c30dbf7e…`, `39fd53e1b98d…`, `8812deb12b2d…`, `d83cc18e15fc…`, `2b9076820e50…`, `2e2afb7701cf…`, `2913175e74c5…`, `cdd0d19e0cc0…`, `bdbcf313230e…`, `14ac4f535f6b…`, `5e4868cc0585…`, `9d2db08f7e1a…`, `c2fbe737d364…`, `b7ae083ccad9…`, `fed168176d72…`, `c47a689322a2…`, `44049e2aace7…`, `35b8bb742727…`, `dbfde3b707dd…`, `54825c63368f…`, `2c8a86d63c3b…`, `315e344a2a20…`, `6f25bb9f83fe…`, `93b0c6284b89…`, `38ab941e6a72…`, `ac16debea5ff…`, `cdc410dd150e…`, `b1ccd4c61a63…`, `dea421dd9003…`, `732df5779588…`, `11270317e6d1…`, `d0898ffd2e82…`, `f0b6168bc28a…`, `fffbd1e700a9…`, `5eb0e6aae43d…`, `72ab350a75e6…`, `fbdb8984b52e…`, `6ca45c096225…`, `b1384b8c3dbd…`, `c3b1aa34f62d…`, `b91dfd50d7c9…`, `73244539c3da…`, `c955c0b1cddd…`, `7c8758dcdc57…`, `cf6fa1de43ca…`, `1c91fc2724e0…`, `054abe1b5fe0…`, `27a8d3479ee2…`, `a6676b9b82cd…`, `2c6dfc61d3aa…`, `8741c631af3e…`, `2afccb815229…`, `25e2d33da2f6…`, `fa5137b405b7…`, `2b2b0c8d5740…`, `ed31e5707fa8…`, `8bbcd2ed367d…`, `71f3ccbf548c…`, `cac0f2e078b6…`, `d3fb55913184…`, `04c1f9088fde…`, `9b58b65f0cb4…`, `64f0c38fe8f4…`, `cf0f682a98c2…`, `734e89af9298…`, `85f26be41bc9…`, `1012c6aa0829…`, `5fffc2ba91a1…`, `26722f3db3b3…`, `f246a682fe18…`, `a3d8f89a50f7…`, `4e81d66eb543…`, `65192f4af950…`, `7748860b7722…`, `1cef530901ae…`, `ae43feeb0bf2…`, `daecf4d7314a…`, `44f09425772e…`, `dc56b3c0b52c…`, `05a39fae2804…`, `a8268bfdaa70…`, `70fb22540709…`, `740d85141ad0…`, `5194b6c89e85…`, `56976d0f1c87…`, `a25c32bdc9bc…`, `c4e2c6dbe9f5…`, `17ff859f9ccc…`, `c4d9fdf73bbe…`, `4fd1395dfc3d…`, `5f24acf38456…`, `cfcfe6439958…`, `293c96afc924…`, `fc231d502c7d…`, `5a196c23f693…`, `e2915f0f5b1b…`, `169fd5df3f92…`, `55415db654c3…`, `28470f70d240…`, `c01da91a8add…`, `563964bd6bd1…`, `4e2063ae947f…`, `8b23d68f76c0…`, `b57a2b778a48…`, `691cf84cf093…`, `0d4c8596a74f…`, `af44ee569a58…`, `376f0ff20209…`, `dc95c67f2a79…`, `0d6cae72bcea…`, `f11b04e990ea…`, `023a80a15e35…`, `f061fe5c1797…`, `da655710835c…`, `8247cdb28ee9…`, `c899e8c48a76…`, `09ed23650d6b…`, `55ce45a6d3ae…`, `7628f0c9dfd9…`, `e77a802f9329…`, `30d7a1fad985…`, `5baefba041c9…`, `b9ee986c63db…`, `54f005e873c0…`, `85a1706041a3…`, `5641e84bda30…`, `4867b3e99182…`, `d4490516b817…`, `eaca515140c5…`, `df69454705fd…`, `9c58896dd05f…`, `973a2060c454…`, `2fb1fa63d66b…`, `5d30950c0518…`, `2e7031f08f08…`, `bd214bff958b…`, `6407b1b5b815…`, `0c4b8a7fc9f6…`, `2d8371b5add0…`, `c8a6810a1a27…`, `b0733f1273c9…`, `eb466653e19e…`, `62276a78e00d…`, `e28c95fd3f77…`, `a41a524dc1ef…`, `ac232eedea56…`, `1ccdac076686…`, `a0aa8c180617…`, `4b8eacc00e04…`, `bd44c0371434…`, `9d6fe7765ef8…`, `c4840a8341fa…`, `ef4522d1d2c1…`, `196cffe0272a…`, `e98903d9acb7…`, `b37ba0936f01…`, `a46589ad75bf…`, `4a1235cd56f2…`, `3a88d35aa4fb…`, `f222e5e9c325…`, `135d98c38610…`, `38e33b6110e8…`, `d296186a0bfc…`, `e8b7188a6fd4…`, `64c50511cde4…`, `f7a8b66a279e…`, `6ed9dd9ff509…`, `fb0e7d35b595…`, `0f7568473e08…`, `fe004409ee18…`, `f97fdb8ab54d…`, `2841045e96cf…`, `84a4b356f6af…`, `48740b0003c4…`, `0bfbd18e7a11…`, `6aec3da4b09a…`, `f14ebbabbc10…`, `f7295bfc8b62…`, `c6db7b7d16f1…`, `c38ec83be850…`, `cbd891e96e74…`, `7de8c32152a1…`, `aa04767a7715…`, `6db0f05d6912…`, `49c366c20462…`, `01bfc158874f…`, `6d0b28ef1c7c…`, `488526ffc145…`, `5155a396b945…`, `56067ea39bbd…`, `cd2f89b2d080…`, `0af903e4cea0…`, `d2e95dd12285…`, `663eb505e54e…`, `5edfc5c6b920…`, `9568fb415f8e…`, `aec723894e42…`, `a0a364b57a51…`, `b157b4be35d1…`, `fd35f824a539…`, `116473610a1f…`, `aedda3d22a88…`, `7c134048dd4e…`, `7f873f50eaa9…`, `c49c404af084…`, `d8938c2d8153…`, `e67ca1f74b25…`, `02cb0586aab9…`, `c3b0dbe3f99c…`, `177d57106ab5…`, `36a750c35117…`, `d5c5eaeeaa15…`, `ce3b3bf8c612…`, `67760a18b0ed…`, `380009336cb5…`, `a972bee93eb1…`, `1616ef5fcba4…`, `905006edf5d9…`, `a57d04ffbb09…`, `ac16adeb6b67…`, `22bd3d759631…`, `ca3fdd0d53b0…`, `92fcda30ec54…`, `03e1f09b7c1d…`, `183d5e630ffb…`, `15f8cdee21cd…`, `cbc1dabbea30…`, `a05098861293…`, `9d46f08ceb5d…`, `8eefa8ee9e3f…`, `ee88f782b67f…`, `3ab20fa5e46f…`, `570edeb9b955…`, `0e40e1ab106b…`, `f7b20e7b9900…`, `f56b04585e1e…`, `4d6242aff42c…`, `5c5c74c9cbe0…`, `8c521895fd03…`, `877da1f7e8ab…`, `24a5f3871400…`, `796c3d33651d…`, `a8b3eb95c333…`, `7eb1f0d63a4c…`, `0f7433341594…`, `a93c7565f7f5…`, `b35d36145d91…`, `326db86dbc5b…`, `4ae9b7d09e1e…`, `6f886901453e…`, `569036880f78…`, `084acf483597…`, `2069e3286041…`, `15c78f2f21ce…`, `521a86cc239e…`, `9d0a50ee706f…`, `9089836bdb82…`, `2b4cb61352ad…`, `7fe63356953e…`, `544ee475f587…`, `99542fe37c07…`, `0515fed44c2e…`, `152c0cc19ce3…`, `270a8f2cbcb8…`, `63a8cfcb02aa…`, `48564350974f…`, `93feddbe2851…`, `019e8dabd717…`, `779e141bb949…`, `7c413966db7b…`, `b08ae4629c0c…`, `316091a1ccf6…`, `2c89f140a212…`, `9d0d58f25eb1…`, `a17259944c33…` |
| `sft-math-nemotron-proofs` | full set | 920,831 | 2,357 | 0 | 2,357 (0.26%) | 918,474 | `8898ae62ec5f…`, `04278dc9f3b5…`, `5a3256975ea6…`, `6210fa7fe8e0…`, `ea29a8869ed9…`, `dbd243b4a5ff…`, `b4795373d8af…`, `e0a60a7898f8…`, `c8e4df68c4fd…`, `6ea94ca2be26…`, `77aa012fcd6f…`, `7b4c528f5e42…`, `3cc573e4855e…`, `0308e7083727…`, `a1d8983dda04…`, `fb6424330498…`, `97730b1883c6…`, `a242cee2e064…`, `01570e9708f8…`, `4e4e6ad06518…`, `ee2698da6f93…`, `7c84375b79df…`, `826c9d1121ca…`, `a5413c0de14a…`, `767d35724877…`, `eb9a61d81180…`, `01a89b0d1bf6…`, `517017ba5163…`, `5de3c8a07ac7…`, `92dbba4bf6da…`, `f2dec3ffa46e…`, `9b549cb94ee7…`, `bed5941de885…`, `82d9db7ceeaf…`, `6e56299965a9…`, `acb6dcbb481e…`, `07e3664d2e7c…`, `87328b3781ed…`, `129fd7ad4e78…`, `9022a80da5ef…`, `4345adaf21a2…`, `3c032567c973…`, `fca9db63afd1…`, `2e26ad5f6362…`, `f5b544402f5d…`, `c3e3a974088b…`, `14464c824150…`, `27b28626566f…`, `48261764d6fd…`, `f009cd1047f0…`, `06e38e930b8f…`, `fd3c8991f3e3…`, `6e5818264428…`, `4e9bf2ae2fe1…`, `88acd4e2c9e7…`, `5f796dcff93d…`, `0cc2cd6cca3a…`, `60866f25712e…`, `1abc1f2b181f…`, `86bc20161e7a…`, `7befa00aa956…`, `c335461b2418…`, `89e431f8b389…`, `ca6e0c0232e1…`, `84670f9a3bf5…`, `ec21d89617f1…`, `5661beb70b35…`, `45995c46b302…`, `24940f031f4e…`, `2a653bb30dea…`, `d0a7d361c72b…`, `4e17af345314…`, `008d588aaa70…`, `94669a276ddf…`, `68432fdc543a…`, `06d904b3baf9…`, `0ca5c94583be…`, `afc1865a0c26…`, `bf119d4abd05…`, `261480aff1ce…`, `9ee438f946b6…`, `22618b863f50…`, `ad0527a04d0e…`, `d0b1434d9e82…`, `6ef8614ee9d5…`, `3bd6692a0323…`, `8eb682915447…`, `0257af4bc126…`, `fba5b2ca3361…`, `8b869f72a4e1…`, `8a3c3e4f34fc…`, `d3500995cca3…`, `3c212eae7b64…`, `3f8867ebf2ff…`, `7e458d07acd8…` |
| `sft-math-nemotron-proofs-v3-sft` | first part, rows within 64k | 1,757 | 42 | 0 | 42 (2.39%) | 1,715 | `77608c18f9ea…` |
| `sft-math-nemotron-sft-math-v4` | full set | 542,117 | 4,776 | 0 | 4,776 (0.88%) | 537,341 | `20c00f0cd256…` |
| `sft-math-openr1-math-raw` | full set | 321,100 | 2,494 | 0 | 2,494 (0.78%) | 318,606 | `299c9de1dc91…`, `355f0aea6e69…`, `cb1e7fc1a9d6…`, `9c05f245cadd…`, `19bf1cf578a6…`, `a82189572d24…`, `9f6a98aab885…`, `0e8bd325f985…`, `16613e4d5645…`, `c7780d5ca16e…`, `8e6b1327e587…`, `80e01c3c678f…`, `83b138c4f432…`, `ae5faab539b5…`, `4c757b6a6b3a…`, `f95fb27d8798…`, `ba4d49fdb526…`, `a6b8b887a03c…`, `301085696e10…`, `c7d25478204a…`, `94f11dd9a4b0…`, `beb29383f0d4…`, `e72f726b2852…`, `cf1e9710273d…`, `f8babf1e849d…`, `f3c8d66ee3f5…`, `74fa3c1bfff3…`, `2daec71002dc…`, `feec0e65c1b8…`, `c32f8e8f0974…`, `5b5f5fced930…`, `e62b8de9eba1…`, `564c556381c7…`, `de6f8bbc4854…`, `130695e6521c…`, `3b909d785c05…`, `a4addf83f0ca…`, `1e585e4081ac…`, `804739d9ba57…` |
| `sft-math-openr1-math` | full set | 224,882 | 1,803 | 0 | 1,803 (0.80%) | 223,079 | `682344d24ba3…`, `cbc8bcb171c9…`, `d7736b348d63…`, `a33ff5ac1edc…`, `2155e5e92cac…`, `0d8c2e5c3de9…`, `75552335c648…`, `36f998d5f8fb…`, `832b5c5c3dc3…`, `bc563c89f1fa…`, `c4b606aaf3ab…`, `35933e6d4603…`, `995b8e6cf0f8…`, `7d869556febb…`, `252ac9a8d858…`, `d241ab7ff755…`, `4aaba5193b88…`, `81500d615610…`, `d027135dc548…`, `733924cab8a8…` |
| `sft-oasst2` | full set | 9,548 | 5 | 0 | 5 (0.05%) | 9,543 | `c89de79a902a…` |
| `sft-rl-math-openmathreasoning` | full set | 3,200,855 | 65,402 | 0 | 65,402 (2.04%) | 3,135,453 | `3284d63609e9…`, `2ebfe35f1169…`, `b891ff3ffe3d…`, `520832e05acd…`, `9b2fb521d086…`, `3e6228811a69…`, `64f8eb745521…`, `34aeb7a4aaa1…`, `3f6de1e2045c…`, `3b2e00e0ca37…`, `aabccd35829f…`, `bf6a83f06264…`, `5ad685c94f4e…`, `450a02276d27…`, `c87c8c300475…`, `8302b952c6cd…`, `9851a061561d…`, `b28049b8eaa5…`, `65a162a500e7…`, `79f804123f09…`, `e66c2a7938ad…`, `bdaf681f56fb…`, `1424654e1b51…`, `9a31959fca15…`, `0d2fe60e1e08…`, `0973862a08a0…`, `a931c74a1baa…`, `f85c4ec8486d…`, `036414affe0a…`, `7961ad01d50b…`, `8048ec925d9a…`, `0810bad23be2…`, `0915a69766c8…`, `968e5fe87db9…`, `271d98a35b27…`, `965a60c859cb…`, `f5af4c909dd6…`, `70301d6ace8d…`, `d06582ea2a51…`, `ff47c8208f23…`, `800478a43cba…`, `664800f89401…`, `aa9724964248…`, `88c559df0dea…`, `32863da72915…`, `5c2c3a5f9696…`, `0e376c442ccd…`, `17b5ba56659c…`, `9b7c3b5e7f74…`, `fe4f81d65c85…`, `8abc21439f6e…`, `c500995414d4…`, `2a2b4793e7d5…`, `f4c40fbe1def…`, `361b36368989…`, `a790a79ade60…`, `31756702a1f3…`, `27391f84d3c2…`, `09cbb21e31df…`, `9014b57e473a…`, `e8a8633c3e2d…`, `afb3bac3099a…`, `ec45b83350ab…`, `d2f8040844aa…`, `51772aa8351b…`, `2eb95931671a…`, `8ba65953b7d9…`, `1f5ef9fe61f0…`, `e924975157ba…`, `05e6afb88a0a…`, `8e043fc6c9df…`, `0b3ce64e59e7…`, `d70df76baa2c…`, `96aba93d6cbc…`, `067702a09740…`, `33d88080d359…`, `2527f17e3659…`, `1707031e676f…`, `1a84c576f8ae…`, `9c5da1a5f251…`, `77ec05509656…`, `6ce066529935…`, `de96d90288bc…`, `bbf4874247b4…`, `f2ef547b6187…`, `985a48db314d…`, `fcb3c7e6452b…`, `d23013785dc1…`, `6e8c71487eff…`, `feaf808d4770…`, `a8158633e360…`, `0fc00a8cc04f…`, `bb2dc602aeac…`, `e164bcf54a25…`, `1d7196e3a022…`, `0af1bc05784a…`, `89bcd415481b…`, `cb3d9424982a…`, `8f726c538ddf…`, `10dd5ad4495e…`, `2457be1c8cd7…`, `22f9db6c3fe3…`, `af6287d63391…`, `b5a07c0ca310…`, `0f0a352cf114…`, `40ae1c6bd42c…`, `982fecf7bbe0…`, `f418b398910a…`, `8e7bd798c20d…`, `bdd5b1c21524…`, `6941859f8e47…`, `be8dfc1a4d2c…`, `d117e2cd75b7…`, `7cc87dfe1055…`, `ef2f0d89686b…`, `94a9c2c76808…`, `8740bed39849…`, `8f4bb2a7c8ca…`, `1285ca30d9bc…`, `14e5f4507f65…`, `256b6d11e3a5…`, `0a85c20646fe…`, `67b2e19bbe0b…`, `6987917ef0d5…`, `72a350c33aca…`, `f2bfef1147a2…`, `2b921b2ffc41…`, `7c2d0ff4e97e…`, `bab6ee297d36…`, `1a894af76156…`, `101c11cd0a95…`, `cfa5fcfe180d…`, `8158bcb2e2a3…`, `e23334b55426…`, `3b381f8d7e4f…`, `fc6f92f069a7…`, `64f5015f2350…`, `08a48287152c…`, `8ac1997d6e29…`, `8fc33da2286c…`, `d740fd41473e…`, `89627e5a5b1b…`, `6c703eff82f3…`, `8f59a39a5cc3…`, `8f245acb29aa…`, `df5c4facc0f1…`, `4bf41fbe08f8…`, `b973ea7b417a…`, `5a86caf8cebe…`, `3574497c5a5e…`, `33b70690dbec…`, `e377700a7105…`, `8f71f9314565…`, `d042a0cefd80…`, `69be3e877699…`, `f18f1804f8ab…`, `64f9a1adbd4b…`, `d5a501c4909a…`, `5fbdaed78b02…`, `9ecca29361e6…`, `84a511b1f9e4…`, `ed22f30081cf…`, `1a2485292fa1…`, `d62db448415a…`, `8b0d596ca5d1…`, `b319c09d9451…`, `79f85a49f086…`, `aff534e743d0…`, `ff3b038bb43f…`, `baab5eef7c9e…`, `372ef3b64007…`, `310b2e704e56…`, `7d7fa9a7c75a…`, `d3dc4e299397…`, `7983a773ff7c…`, `125bde84972e…`, `c3ed02482301…`, `f4aa7224b735…`, `68ea0b01a8ba…`, `ce73ea854ccf…`, `48e3d9a7e72d…`, `808b94a105d4…`, `9e510c662661…`, `e192a7bc7fb9…`, `e7a63a09a4a6…`, `5b3205d1b158…`, `fc3fe93d038f…`, `94b6144c849f…`, `a846b7f2a174…`, `a03ebd1fb0ff…`, `9a061321e26b…`, `57d91c731573…`, `990e922feafb…`, `cd7e715104ee…`, `177640130602…`, `060c77f1703f…`, `54b336fdecdf…`, `482cfd896398…`, `f952e3c8c8b5…`, `5d598a7978e4…`, `f1eb466bc90a…`, `6fdb4b9b10ca…`, `7acb39ce853b…`, `a0fe81fd1457…`, `f2ea5af2eaf8…`, `5a35b4f24ae5…`, `a121b5585f6a…`, `9ea28483c52d…`, `cbea13314fec…`, `dbec9869fd37…`, `ad99b69d8f30…`, `fd71f17f1e82…`, `01abb629e4fa…`, `633de527a6ef…`, `9e5de8472a82…`, `62882f05772c…`, `3c3e5e03c5d6…`, `c0fe56517bba…`, `5b12b9b07a9e…`, `8c83b71196f1…`, `5b526b7c71b9…`, `0645bc031ba0…`, `771476a69c76…`, `1d835fcb15ed…`, `a0542e1169c1…`, `2051a914e0f5…`, `d8ab807c3ece…`, `2ae0d6c94166…`, `29f6ea4ed8e7…`, `57ec01e19aaa…`, `02e426282e4b…`, `657f60c6bc75…`, `4d542e60e094…`, `e367d8ff2055…`, `a73c88e137cf…`, `f2cf9ba57501…`, `1d694feef564…`, `127e37c9a9b2…`, `74c5e268af4b…`, `21d851837e17…`, `866fbe7778d4…`, `ebb323e06fbb…`, `3428f453d6f0…`, `8a4a80ab1ade…`, `dbc4cfca3c9a…`, `2a69a13f0db9…`, `6fd204c0e308…`, `bc5127ec8e71…`, `3d40b8e17e17…`, `637e567abc5d…`, `3ad763bf4e47…`, `6990473816d3…`, `20948c21cbb2…`, `fbb24159ba62…`, `db6dc23bd1dc…`, `02ba704849df…`, `010a9cf0e254…`, `3f2ae3d475eb…`, `a9089b72ef2f…`, `755eaf7d30f5…`, `3f7cb7fdd4e8…`, `9b85b7108b1b…`, `ebcc01809919…`, `9285222a2ded…`, `4bc140a21191…`, `50e4511b512d…`, `7f9197576241…`, `5fb7c8195d05…`, `0028853c9f1a…`, `497f6dcc2762…`, `57d05c48b679…`, `ce7795908cf9…`, `3478a670c196…`, `7767d673d04c…`, `b83163a038ca…`, `462701dc7a30…`, `1d729cf6054d…`, `9ec32a58240d…`, `3edc49665928…`, `ac910d699bc1…`, `9df36add01b5…`, `418db412a5fe…`, `91a172c3a456…`, `ae1840e4674c…`, `f630e75059d5…`, `d0443ea106d7…`, `1515ab0e5ccc…`, `86f50f583105…` |
| `sft-salesforce-xlam-60k` | full set | 60,000 | 182 | 0 | 182 (0.30%) | 59,818 | `77369e312a59…` |
| `sft-science-glm51-phd` | full set | 103,702 | 207 | 0 | 207 (0.20%) | 103,495 | `54d681c1edc8…` |
| `sft-science-nemotron-science-v2` | full set | 96,605 | 286 | 0 | 286 (0.30%) | 96,319 | `390c839aae1b…` |
| `sft-science-nemotron-science` | full set | 174,155 | 369 | 0 | 369 (0.21%) | 173,786 | `6f9ac4dc35a0…` |
| `sft-stem-code-openthoughts3` | full set | 450,599 | 7,457 | 0 | 7,457 (1.65%) | 443,142 | `79f4ff26c091…`, `ade7c9a57a9a…`, `339d8d7a2365…`, `6cd690ad6162…`, `bfc8889fd947…`, `bbf06c20198f…`, `c0b69a521656…`, `050dc50cc113…`, `78b37d9adaaf…`, `45112561996b…`, `df2a24c8ffb1…`, `035b09e8392d…`, `e91b9317cf4f…`, `79c54c847f81…`, `f1fd1a47c906…`, `fb0dc7686647…`, `6f98a681965c…`, `3b9ce3d515f8…`, `06de3c49caa6…`, `7b5c21530b81…`, `b68890d2f196…`, `e96250c2c5dd…`, `47ffd65a22c6…`, `f97a16876b62…`, `b2eda5876be9…`, `784f6476778e…`, `9ee3aeb836ee…`, `4f9a39e0d2b6…`, `82a3e0878dfc…`, `8e49fff488bb…`, `24eab6e1e40f…`, `a0a74c9b6662…`, `6db44fc142f7…`, `b49184e84ecb…`, `08ef9e409887…`, `759d62dea723…`, `4aa6cd514c76…`, `16315ac38c30…`, `a14c07d455d4…`, `ac423827f18d…`, `2b150183b97b…`, `28c038ede56f…`, `17a8a8b4699f…`, `d25d0d3cb5c8…`, `3bfa28c90937…`, `c8535b6b24c3…`, `7170551799f6…`, `980940982da2…`, `0cfbbf6fe7ff…`, `6278731204e0…`, `f46e39ba4445…`, `a008b84b3403…`, `b75cec629a02…`, `180233fa0a0d…`, `f4ddf86d1768…`, `176a98edadd0…`, `c8fd43f1ca01…`, `0490573de419…`, `7d1a10cca633…`, `c5451affbdb0…`, `ad0ee9308e89…`, `5ac1e4c7b8ae…`, `2d06beeec41a…`, `c562fc524337…`, `60e57ff96219…`, `90f37ab833e4…`, `ac39bc75d9e3…`, `2e5bcc6805e3…`, `ab93ee9ddac1…`, `89b9caa7b479…`, `9b24af20c6fa…`, `85eb8b58180d…`, `86b2cb843c66…`, `8aa42a3c0b7e…`, `0d92bbe5c35d…`, `96ff98da4576…`, `2f57f6cdd449…`, `e4ca30295e37…`, `a97bfbbb54de…`, `e7ac6d81e8bb…`, `5b5d250c2b15…`, `a48fdf3f83fb…`, `622db5de91b8…`, `14fd7d1bcb25…`, `fc679955203f…`, `41d40a253c48…`, `2995815864d7…`, `697f08fa7820…`, `b418bdfc940c…`, `6f6683ebeeac…`, `5e654702115f…`, `6aa5102da92c…`, `a07c687c112b…`, `37bae8c93b88…`, `1ad5a7501c96…`, `eab3dc4bb945…`, `f813e452f827…`, `2e749834981f…`, `6e843ee19136…`, `4ffba978fc49…`, `144580db0fe3…`, `976ee17bcc51…`, `1dc640b953af…`, `248755862922…`, `ad4367db46ce…`, `0e0ae3cf1233…`, `6331f959579d…`, `b4e65d14ef97…`, `b470a1881d98…`, `23029aeec603…`, `087a9770b759…`, `80865aa19021…`, `af50e4d4dcf2…`, `d99412775cec…`, `fa8706efcf46…`, `38a251e43b1b…`, `d6f01e3864e4…`, `6252a408aa3b…`, `124f8b845375…`, `f6eb39dfe732…` |
| `sft-safety-aegis-v1` | text column, train and test, not chat | 11,997 | 2 | 0 | 2 (0.02%) | 11,995 | `e545b24def6c…` |
| **Total** | | **17,438,781** | **460,409** | **0** | **460,409** (2.64%) | **16,978,372** | |

`sft-code-opencodereasoning-2` raw input is 1,398,166 rows. Before the scan, 268,752 are upstream test splits, 3,629 are protected family, 513,809 fail the quality proposal, and 69,690 are held because the `open-r1/codeforces` revision is not established. The other 542,286 join; 67 are rejected by the converter, so 542,219 reach the scan.

**Run on** says what was checked: *full set* is every row the converter produced from the whole source (30 sets); *sample* is the first rows of a split only (0 sets), and is not cleared as a whole.

A row that is both flagged and carries a canary counts once in Removed.

## 2. Flagged documents by benchmark

| Set | `aime_2024` | `aime_2025` | `bfcl_v3` | `codeforces` | `flores200` | `gaia` | `gpqa_diamond` | `gsm8k` | `heldout_g5_v1` | `hle` | `in22_conv` | `in22_gen` | `livecodebench` | `longbench_v2` | `milu` | `mmlu` | `swe_bench_live` | `swe_bench_pro` | `swe_bench_verified` | `terminal_bench_2` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `sft-agentic-nemotron-agentic-v1` | 0 | 0 | 66 | 0 | 6 | 0 | 0 | 0 | 0 | 27 | 2 | 0 | 6 | 0 | 43 | 6 | 277 | 0 | 0 | 0 |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | 0 | 1 | 135 | 1 | 0 | 0 | 0 | 1 | 16 | 18 | 3 | 2 | 636 | 0 | 30 | 14 | 1185 | 12 | 26 | 72 |
| `sft-bespoke-stratos-17k` | 87 | 73 | 1 | 1010 | 0 | 1 | 1 | 0 | 2 | 122 | 0 | 0 | 838 | 0 | 3 | 99 | 0 | 0 | 0 | 0 |
| `sft-chat-nemotron-if-v1` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| `sft-chat-nemotron-if-v2` | 322 | 287 | 540 | 61 | 2 | 14 | 2 | 240 | 3 | 559 | 38 | 2 | 461 | 4 | 176 | 1425 | 1916 | 15 | 29 | 31 |
| `sft-code-codeforces-cots` | 0 | 0 | 0 | 19253 | 0 | 5 | 0 | 0 | 6 | 1738 | 0 | 0 | 10720 | 0 | 1 | 1 | 0 | 0 | 0 | 0 |
| `sft-code-commitpackft` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 7 | 0 |
| `sft-code-nemotron-cascade-swe` | 0 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 1 | 30 | 68 | 0 | 2 | 0 | 0 | 5 | 14799 | 2613 | 4375 | 4 |
| `sft-code-nemotron-cuda` | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sft-code-nemotron-opencode` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 332 | 0 | 0 | 0 |
| `sft-code-nemotron-terminal` | 0 | 0 | 0 | 7812 | 0 | 2 | 0 | 0 | 3 | 183 | 0 | 0 | 5743 | 0 | 2 | 0 | 9 | 2 | 0 | 0 |
| `sft-code-opencodereasoning` | 0 | 1 | 0 | 73195 | 0 | 45 | 0 | 0 | 41 | 2573 | 1 | 0 | 65305 | 0 | 3 | 6 | 0 | 7 | 0 | 0 |
| `sft-code-opencodereasoning-2` | 0 | 0 | 0 | 2231 | 0 | 0 | 0 | 0 | 0 | 71 | 0 | 0 | 2662 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| `sft-code-swe-rebench-openhands` | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 1 | 0 | 0 | 0 | 4474 | 21 | 1058 | 0 |
| `sft-code-swe-zero-openhands` | 0 | 0 | 16 | 23 | 0 | 0 | 0 | 0 | 0 | 111 | 22 | 0 | 3 | 1 | 5 | 16 | 19751 | 255 | 6051 | 2 |
| `sft-dolly-15k` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 |
| `sft-indic-aya-collection` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sft-indic-aya-dataset` | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 |
| `sft-indic-indic-align-dolly-t` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sft-indic-indic-align-oasst-t` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sft-math-nemotron-math-v2` | 11104 | 10767 | 21 | 2232 | 0 | 3 | 395 | 0 | 161 | 24253 | 0 | 0 | 6861 | 9 | 18 | 2287 | 11227 | 20 | 792 | 0 |
| `sft-math-nemotron-proofs` | 84 | 9 | 1 | 326 | 0 | 12 | 32 | 0 | 32 | 1438 | 0 | 0 | 359 | 0 | 1 | 166 | 0 | 0 | 0 | 0 |
| `sft-math-nemotron-proofs-v3-sft` | 5 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 32 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sft-math-nemotron-sft-math-v4` | 225 | 308 | 1 | 199 | 0 | 1 | 65 | 0 | 52 | 3070 | 0 | 0 | 574 | 1 | 6 | 228 | 299 | 10 | 66 | 0 |
| `sft-math-openr1-math-raw` | 321 | 121 | 11 | 327 | 0 | 1 | 31 | 0 | 13 | 1480 | 0 | 0 | 318 | 0 | 42 | 71 | 0 | 0 | 0 | 0 |
| `sft-math-openr1-math` | 354 | 279 | 14 | 99 | 0 | 0 | 30 | 0 | 7 | 1053 | 0 | 0 | 132 | 0 | 38 | 72 | 0 | 0 | 0 | 0 |
| `sft-oasst2` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 2 | 1 | 1 | 0 | 0 | 0 |
| `sft-rl-math-openmathreasoning` | 18233 | 14606 | 64 | 3962 | 0 | 15 | 1300 | 0 | 297 | 33251 | 0 | 0 | 4352 | 0 | 17 | 2712 | 0 | 13 | 0 | 0 |
| `sft-salesforce-xlam-60k` | 0 | 0 | 164 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 1 | 0 | 13 | 0 | 0 | 0 |
| `sft-science-glm51-phd` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 207 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `sft-science-nemotron-science-v2` | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 183 | 0 | 0 | 0 | 0 | 34 | 74 | 2 | 0 | 0 | 0 |
| `sft-science-nemotron-science` | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 272 | 0 | 0 | 0 | 0 | 42 | 68 | 0 | 0 | 0 | 0 |
| `sft-stem-code-openthoughts3` | 213 | 171 | 16 | 4066 | 0 | 15 | 24 | 0 | 5 | 2335 | 0 | 0 | 705 | 0 | 75 | 149 | 2 | 10 | 0 | 0 |
| `sft-safety-aegis-v1` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |

A document is flagged when it shares at least one 13-word run (20 tokens for code) with a benchmark item. The whole document is removed. The count is documents per benchmark, so a document that matches two benchmarks counts in both columns.

## 3. Flagged documents by coverage

Coverage is the share of one benchmark item's runs that the document contains (the highest over its hits). The bands are for reading the result; every flagged document is removed whatever its band.

| Set | Flagged | Coverage 0.5 or more | 0.1 to 0.5 | Below 0.1 |
|---|---:|---:|---:|---:|
| `sft-agentic-nemotron-agentic-v1` | 432 | 4 | 53 | 375 |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | 2146 | 27 | 259 | 1860 |
| `sft-bespoke-stratos-17k` | 1791 | 38 | 73 | 1680 |
| `sft-chat-nemotron-if-v1` | 1 | 0 | 1 | 0 |
| `sft-chat-nemotron-if-v2` | 5820 | 669 | 1011 | 4140 |
| `sft-code-codeforces-cots` | 20796 | 45 | 1563 | 19188 |
| `sft-code-nemotron-cascade-swe` | 18248 | 211 | 1620 | 16417 |
| `sft-code-nemotron-cuda` | 2 | 0 | 0 | 2 |
| `sft-code-nemotron-opencode` | 332 | 0 | 0 | 332 |
| `sft-code-nemotron-terminal` | 9901 | 321 | 454 | 9126 |
| `sft-code-opencodereasoning` | 112753 | 0 | 1311 | 111442 |
| `sft-code-swe-rebench-openhands` | 4864 | 147 | 263 | 4454 |
| `sft-code-swe-zero-openhands` | 22167 | 222 | 2230 | 19715 |
| `sft-dolly-15k` | 4 | 0 | 1 | 3 |
| `sft-indic-aya-collection` | 6 | 1 | 0 | 5 |
| `sft-indic-aya-dataset` | 8 | 1 | 2 | 5 |
| `sft-indic-indic-align-dolly-t` | 0 | 0 | 0 | 0 |
| `sft-indic-indic-align-oasst-t` | 9 | 0 | 3 | 6 |
| `sft-math-nemotron-math-v2` | 60665 | 1 | 827 | 59837 |
| `sft-math-nemotron-proofs` | 2357 | 0 | 8 | 2349 |
| `sft-math-nemotron-sft-math-v4` | 4776 | 0 | 42 | 4734 |
| `sft-math-openr1-math-raw` | 2494 | 0 | 39 | 2455 |
| `sft-math-openr1-math` | 1803 | 0 | 50 | 1753 |
| `sft-oasst2` | 5 | 0 | 3 | 2 |
| `sft-rl-math-openmathreasoning` | 65402 | 639 | 1890 | 62873 |
| `sft-salesforce-xlam-60k` | 182 | 13 | 53 | 116 |
| `sft-science-glm51-phd` | 207 | 0 | 0 | 207 |
| `sft-science-nemotron-science-v2` | 286 | 0 | 6 | 280 |
| `sft-science-nemotron-science` | 369 | 0 | 3 | 366 |
| `sft-stem-code-openthoughts3` | 7457 | 0 | 40 | 7417 |

## 4. Benchmark items with the largest overlap

**`sft-agentic-nemotron-agentic-v1`**: at least 44 different benchmark items found in 432 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `bfcl_v3:test:live_irrelevance_719-238-0` | 2 | 1.000 | 1 / 1 | `sft-agentic-nemotron-agentic-v1/179971` | 12558 |
| `bfcl_v3:test:simple_336` | 1 | 1.000 | 1 / 1 | `sft-agentic-nemotron-agentic-v1/117494` | 1382 |
| `bfcl_v3:test:simple_0` | 2 | 0.800 | 4 / 5 | `sft-agentic-nemotron-agentic-v1/227915` | 975 |
| `mmlu:test:5882` | 3 | 0.451 | 107 / 237 | `sft-agentic-nemotron-agentic-v1/21810` | 5053 |
| `mmlu:test:6050` | 3 | 0.439 | 107 / 244 | `sft-agentic-nemotron-agentic-v1/21810` | 5053 |
| `mmlu:test:5857` | 3 | 0.431 | 107 / 248 | `sft-agentic-nemotron-agentic-v1/21810` | 5053 |
| `mmlu:test:5962` | 3 | 0.392 | 107 / 273 | `sft-agentic-nemotron-agentic-v1/21810` | 5053 |
| `milu:test:12344` | 37 | 0.289 | 11 / 38 | `sft-agentic-nemotron-agentic-v1/4106` | 7675 |
| `bfcl_v3:test:parallel_19` | 4 | 0.176 | 3 / 17 | `sft-agentic-nemotron-agentic-v1/114753` | 1367 |
| `milu:test:19953` | 2 | 0.167 | 1 / 6 | `sft-agentic-nemotron-agentic-v1/36422` | 42473 |
| `milu:test:18206` | 2 | 0.151 | 8 / 53 | `sft-agentic-nemotron-agentic-v1/57058` | 35190 |
| `bfcl_v3:test:parallel_145` | 12 | 0.133 | 4 / 30 | `sft-agentic-nemotron-agentic-v1/34328` | 1959 |
| `mmlu:test:5718` | 1 | 0.128 | 19 / 148 | `sft-agentic-nemotron-agentic-v1/297793` | 13058 |
| `mmlu:test:5752` | 1 | 0.124 | 19 / 153 | `sft-agentic-nemotron-agentic-v1/297793` | 13058 |
| `mmlu:test:5680` | 1 | 0.119 | 19 / 160 | `sft-agentic-nemotron-agentic-v1/297793` | 13058 |

**`sft-agentic-nemotron-sft-agentic-v2-tool-calling`**: at least 135 different benchmark items found in 2146 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `bfcl_v3:test:simple_336` | 1 | 1.000 | 1 / 1 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/170675` | 3274 |
| `bfcl_v3:test:simple_379` | 1 | 1.000 | 1 / 1 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/343534` | 2078 |
| `bfcl_v3:test:simple_9` | 12 | 1.000 | 1 / 1 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/22611` | 349 |
| `livecodebench:release_v6:3461` | 252 | 0.775 | 93 / 120 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/96905` | 12160 |
| `heldout_g5_v1:heldout:pes2o-val-000124` | 10 | 0.623 | 48 / 77 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/101126` | 52488 |
| `gsm8k:test:42` | 1 | 0.458 | 54 / 118 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/196745` | 121203 |
| `mmlu:test:5882` | 2 | 0.451 | 107 / 237 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/73659` | 4345 |
| `gsm8k:test:40` | 1 | 0.439 | 25 / 57 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/196745` | 117086 |
| `mmlu:test:6050` | 2 | 0.439 | 107 / 244 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/73659` | 4345 |
| `mmlu:test:5857` | 2 | 0.431 | 107 / 248 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/73659` | 4345 |
| `livecodebench:release_v6:3748` | 96 | 0.422 | 81 / 192 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/35210` | 16187 |
| `mmlu:test:5962` | 2 | 0.392 | 107 / 273 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/73659` | 4345 |
| `gsm8k:test:71` | 1 | 0.391 | 25 / 64 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/196745` | 125785 |
| `gsm8k:test:55` | 1 | 0.378 | 17 / 45 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/196745` | 117563 |
| `gsm8k:test:3` | 1 | 0.371 | 13 / 35 | `sft-agentic-nemotron-sft-agentic-v2-tool-calling/196745` | 116743 |

**`sft-bespoke-stratos-17k`**: at least 864 different benchmark items found in 1791 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `mmlu:test:4291` | 1 | 0.860 | 74 / 86 | `sft-bespoke-stratos-17k/8225` | 111 |
| `mmlu:test:4279` | 1 | 0.855 | 71 / 83 | `sft-bespoke-stratos-17k/7617` | 111 |
| `mmlu:test:4393` | 1 | 0.829 | 58 / 70 | `sft-bespoke-stratos-17k/7103` | 111 |
| `mmlu:test:4423` | 1 | 0.821 | 55 / 67 | `sft-bespoke-stratos-17k/3900` | 111 |
| `mmlu:test:4302` | 1 | 0.778 | 42 / 54 | `sft-bespoke-stratos-17k/3719` | 111 |
| `mmlu:test:4384` | 1 | 0.778 | 42 / 54 | `sft-bespoke-stratos-17k/7505` | 111 |
| `mmlu:test:4263` | 1 | 0.765 | 39 / 51 | `sft-bespoke-stratos-17k/4632` | 111 |
| `mmlu:test:4399` | 1 | 0.745 | 35 / 47 | `sft-bespoke-stratos-17k/5292` | 111 |
| `mmlu:test:4457` | 1 | 0.733 | 33 / 45 | `sft-bespoke-stratos-17k/5216` | 111 |
| `mmlu:test:4360` | 1 | 0.692 | 27 / 39 | `sft-bespoke-stratos-17k/7653` | 111 |
| `mmlu:test:4451` | 1 | 0.692 | 27 / 39 | `sft-bespoke-stratos-17k/5609` | 111 |
| `mmlu:test:4460` | 1 | 0.676 | 25 / 37 | `sft-bespoke-stratos-17k/4457` | 111 |
| `mmlu:test:4261` | 1 | 0.657 | 23 / 35 | `sft-bespoke-stratos-17k/4603` | 111 |
| `mmlu:test:4262` | 3 | 0.657 | 23 / 35 | `sft-bespoke-stratos-17k/6359` | 111 |
| `mmlu:test:4303` | 1 | 0.657 | 23 / 35 | `sft-bespoke-stratos-17k/3229` | 111 |

**`sft-chat-nemotron-if-v1`**: at least 1 different benchmark items found in 1 documents (top 1 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `milu:test:12344` | 1 | 0.289 | 11 / 38 | `sft-chat-nemotron-if-v1/3111` | 7832 |

**`sft-chat-nemotron-if-v2`**: at least 1048 different benchmark items found in 5820 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `bfcl_v3:test:irrelevance_139` | 1 | 1.000 | 1 / 1 | `sft-chat-nemotron-if-v2/664081` | 67 |
| `bfcl_v3:test:live_irrelevance_719-238-0` | 2 | 1.000 | 1 / 1 | `sft-chat-nemotron-if-v2/199664` | 2086 |
| `flores200:dev+devtest:dev:eng_Latn:596` | 1 | 1.000 | 1 / 1 | `sft-chat-nemotron-if-v2/621137` | 9237 |
| `mmlu:test:1424` | 1 | 0.948 | 73 / 77 | `sft-chat-nemotron-if-v2/744064` | 77 |
| `mmlu:test:1440` | 1 | 0.915 | 65 / 71 | `sft-chat-nemotron-if-v2/646165` | 77 |
| `mmlu:test:12326` | 1 | 0.881 | 52 / 59 | `sft-chat-nemotron-if-v2/811485` | 67 |
| `mmlu:test:4291` | 18 | 0.872 | 75 / 86 | `sft-chat-nemotron-if-v2/550798` | 331 |
| `mmlu:test:4279` | 20 | 0.867 | 72 / 83 | `sft-chat-nemotron-if-v2/576972` | 3781 |
| `mmlu:test:601` | 1 | 0.857 | 6 / 7 | `sft-chat-nemotron-if-v2/772946` | 77 |
| `mmlu:test:672` | 4 | 0.857 | 6 / 7 | `sft-chat-nemotron-if-v2/31734` | 185 |
| `mmlu:test:100` | 11 | 0.848 | 67 / 79 | `sft-chat-nemotron-if-v2/902982` | 67 |
| `mmlu:test:4423` | 11 | 0.836 | 56 / 67 | `sft-chat-nemotron-if-v2/159143` | 770 |
| `mmlu:test:3472` | 9 | 0.833 | 5 / 6 | `sft-chat-nemotron-if-v2/23309` | 1071 |
| `mmlu:test:4393` | 10 | 0.829 | 58 / 70 | `sft-chat-nemotron-if-v2/55826` | 3343 |
| `livecodebench:release_v6:2792` | 1 | 0.820 | 169 / 206 | `sft-chat-nemotron-if-v2/168382` | 67 |

**`sft-code-codeforces-cots`**: at least 544 different benchmark items found in 20796 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `livecodebench:release_v6:1899_D` | 473 | 0.883 | 355 / 402 | `sft-code-codeforces-cots/12840` | 461 |
| `livecodebench:release_v6:1883_B` | 186 | 0.871 | 371 / 426 | `sft-code-codeforces-cots/10455` | 462 |
| `livecodebench:release_v6:1899_B` | 157 | 0.868 | 356 / 410 | `sft-code-codeforces-cots/27580` | 807 |
| `livecodebench:release_v6:1883_C` | 703 | 0.837 | 272 / 325 | `sft-code-codeforces-cots/22480` | 807 |
| `livecodebench:release_v6:1873_D` | 516 | 0.796 | 215 / 270 | `sft-code-codeforces-cots/37935` | 806 |
| `livecodebench:release_v6:1899_C` | 298 | 0.769 | 163 / 212 | `sft-code-codeforces-cots/40055` | 807 |
| `livecodebench:release_v6:1873_B` | 958 | 0.739 | 119 / 161 | `sft-code-codeforces-cots/44217` | 807 |
| `livecodebench:release_v6:1873_A` | 326 | 0.694 | 161 / 232 | `sft-code-codeforces-cots/44420` | 806 |
| `livecodebench:release_v6:1899_A` | 35 | 0.683 | 95 / 139 | `sft-code-codeforces-cots/11290` | 462 |
| `hle:test:66ed458ed841eb51a985ca8d` | 5 | 0.429 | 175 / 408 | `sft-code-codeforces-cots/5090` | 452 |
| `hle:test:672f6cfd609b665328565e5c` | 5 | 0.343 | 109 / 318 | `sft-code-codeforces-cots/8195` | 461 |
| `codeforces:test:2018/B` | 3878 | 0.267 | 56 / 210 | `sft-code-codeforces-cots/33780` | 1391 |
| `codeforces:test:2060/D` | 2117 | 0.248 | 53 / 214 | `sft-code-codeforces-cots/1095` | 1479 |
| `hle:test:672f72e3609b665328565e6b` | 5 | 0.213 | 112 / 526 | `sft-code-codeforces-cots/37475` | 806 |
| `codeforces:test:2018/A` | 139 | 0.209 | 83 / 398 | `sft-code-codeforces-cots/4730` | 462 |

**`sft-code-nemotron-cascade-swe`**: at least 630 different benchmark items found in 18248 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `swe_bench_live:test:beeware__briefcase-1867` | 1 | 1.000 | 51 / 51 | `sft-code-nemotron-cascade-swe/200008959` | 181 |
| `swe_bench_live:test:conan-io__conan-15699` | 34 | 1.000 | 238 / 238 | `sft-code-nemotron-cascade-swe/100001423` | 180 |
| `swe_bench_live:test:conan-io__conan-15931` | 108 | 1.000 | 49 / 49 | `sft-code-nemotron-cascade-swe/100003235` | 180 |
| `swe_bench_live:test:streamlink__streamlink-5926` | 74 | 0.996 | 278 / 279 | `sft-code-nemotron-cascade-swe/100017100` | 179 |
| `swe_bench_live:test:streamlink__streamlink-5908` | 9 | 0.973 | 358 / 368 | `sft-code-nemotron-cascade-swe/37451` | 256 |
| `swe_bench_live:test:icloud-photos-downloader__icloud_photos_downloader-1060` | 7 | 0.964 | 319 / 331 | `sft-code-nemotron-cascade-swe/100011480` | 179 |
| `swe_bench_live:test:streamlink__streamlink-6420` | 39 | 0.954 | 352 / 369 | `sft-code-nemotron-cascade-swe/100010333` | 180 |
| `swe_bench_live:test:wireservice__csvkit-1281` | 1 | 0.943 | 477 / 506 | `sft-code-nemotron-cascade-swe/45056` | 256 |
| `swe_bench_live:test:streamlink__streamlink-6242` | 136 | 0.924 | 171 / 185 | `sft-code-nemotron-cascade-swe/100000310` | 179 |
| `swe_bench_live:test:beeware__briefcase-1638` | 8 | 0.920 | 103 / 112 | `sft-code-nemotron-cascade-swe/100011261` | 180 |
| `swe_bench_live:test:streamlink__streamlink-6353` | 101 | 0.904 | 311 / 344 | `sft-code-nemotron-cascade-swe/100003763` | 179 |
| `swe_bench_live:test:kedro-org__kedro-3715` | 20 | 0.875 | 1290 / 1474 | `sft-code-nemotron-cascade-swe/61028` | 256 |
| `swe_bench_live:test:streamlink__streamlink-6207` | 10 | 0.866 | 629 / 726 | `sft-code-nemotron-cascade-swe/100000595` | 179 |
| `swe_bench_live:test:pdm-project__pdm-3393` | 7 | 0.852 | 1584 / 1860 | `sft-code-nemotron-cascade-swe/41285` | 258 |
| `swe_bench_live:test:streamlink__streamlink-5844` | 8 | 0.830 | 597 / 719 | `sft-code-nemotron-cascade-swe/100001030` | 179 |

**`sft-code-nemotron-cuda`**: at least 2 different benchmark items found in 2 documents (top 2 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `hle:test:6726c7e9d2ad475e400669c7` | 1 | 0.002 | 1 / 635 | `sft-code-nemotron-cuda/952` | 30663 |
| `codeforces:test:2055/C` | 1 | 0.001 | 1 / 885 | `sft-code-nemotron-cuda/272` | 15733 |

**`sft-code-nemotron-opencode`**: at least 3 different benchmark items found in 332 documents (top 3 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `swe_bench_live:test:streamlink__streamlink-6111` | 318 | 0.014 | 4 / 290 | `sft-code-nemotron-opencode/388` | 55945 |
| `swe_bench_live:test:kozea__weasyprint-2326` | 11 | 0.006 | 3 / 545 | `sft-code-nemotron-opencode/11431` | 107288 |
| `swe_bench_live:test:lss233__kirara-ai-1445` | 3 | 0.000 | 3 / 11774 | `sft-code-nemotron-opencode/3800` | 104386 |

**`sft-code-nemotron-terminal`**: at least 1034 different benchmark items found in 9901 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `codeforces:test:2041/K` | 8 | 0.978 | 619 / 633 | `sft-code-nemotron-terminal/18418` | 2924 |
| `codeforces:test:2005/C` | 12 | 0.977 | 597 / 611 | `sft-code-nemotron-terminal/20488` | 2924 |
| `codeforces:test:2036/E` | 3 | 0.977 | 644 / 659 | `sft-code-nemotron-terminal/27896` | 2924 |
| `codeforces:test:2045/D` | 1 | 0.977 | 558 / 571 | `sft-code-nemotron-terminal/15045` | 2924 |
| `codeforces:test:2038/A` | 161 | 0.976 | 569 / 583 | `sft-code-nemotron-terminal/6020` | 2924 |
| `codeforces:test:2053/I2` | 14 | 0.976 | 648 / 664 | `sft-code-nemotron-terminal/14967` | 2924 |
| `codeforces:test:2053/D` | 35 | 0.975 | 584 / 599 | `sft-code-nemotron-terminal/1107` | 2924 |
| `codeforces:test:2037/F` | 10 | 0.974 | 520 / 534 | `sft-code-nemotron-terminal/3412` | 2924 |
| `codeforces:test:2045/M` | 3 | 0.974 | 482 / 495 | `sft-code-nemotron-terminal/14150` | 2924 |
| `codeforces:test:2056/E` | 63 | 0.974 | 530 / 544 | `sft-code-nemotron-terminal/6225` | 2924 |
| `codeforces:test:1993/E` | 12 | 0.972 | 527 / 542 | `sft-code-nemotron-terminal/28570` | 2924 |
| `codeforces:test:2029/I` | 41 | 0.972 | 492 / 506 | `sft-code-nemotron-terminal/25304` | 2923 |
| `codeforces:test:2034/F1` | 40 | 0.972 | 630 / 648 | `sft-code-nemotron-terminal/9760` | 2924 |
| `codeforces:test:2037/D` | 10 | 0.972 | 486 / 500 | `sft-code-nemotron-terminal/1247` | 2924 |
| `codeforces:test:2049/D` | 19 | 0.972 | 480 / 494 | `sft-code-nemotron-terminal/19100` | 2924 |

**`sft-code-opencodereasoning`**: at least 990 different benchmark items found in 112753 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `hle:test:66ed458ed841eb51a985ca8d` | 40 | 0.471 | 192 / 408 | `sft-code-opencodereasoning/2000007388` | 67 |
| `hle:test:672f6cfd609b665328565e5c` | 38 | 0.421 | 134 / 318 | `sft-code-opencodereasoning/2000007984` | 67 |
| `hle:test:672f72e3609b665328565e6b` | 39 | 0.238 | 125 / 526 | `sft-code-opencodereasoning/700002908` | 67 |
| `hle:test:66eeea0187ec4a6a04092e78` | 757 | 0.192 | 79 / 412 | `sft-code-opencodereasoning/2300013191` | 194 |
| `hle:test:673627bc10ec0a5f859365ce` | 40 | 0.188 | 69 / 368 | `sft-code-opencodereasoning/700003608` | 928 |
| `hle:test:67373220a4d09488d430f640` | 40 | 0.185 | 69 / 373 | `sft-code-opencodereasoning/700003608` | 928 |
| `hle:test:672e24f117ed86a6ef9def55` | 40 | 0.183 | 72 / 393 | `sft-code-opencodereasoning/2000000557` | 67 |
| `codeforces:test:2018/B` | 10508 | 0.181 | 38 / 210 | `sft-code-opencodereasoning/2300014462` | 857 |
| `codeforces:test:2038/B` | 8186 | 0.169 | 30 / 178 | `sft-code-opencodereasoning/2500005210` | 502 |
| `codeforces:test:2060/D` | 6875 | 0.159 | 34 / 214 | `sft-code-opencodereasoning/2300015043` | 781 |
| `codeforces:test:2010/A` | 3828 | 0.151 | 16 / 106 | `sft-code-opencodereasoning/2300014197` | 673 |
| `codeforces:test:2056/D` | 4717 | 0.150 | 41 / 273 | `sft-code-opencodereasoning/2300012583` | 1048 |
| `livecodebench:release_v6:1873_B` | 4755 | 0.149 | 24 / 161 | `sft-code-opencodereasoning/2300014293` | 943 |
| `in22_conv:test:6-2` | 1 | 0.143 | 1 / 7 | `sft-code-opencodereasoning/1100017410` | 44316 |
| `hle:test:66f28a89f1256af80477e15d` | 40 | 0.136 | 100 / 733 | `sft-code-opencodereasoning/2000001343` | 67 |

**`sft-code-swe-rebench-openhands`**: at least 248 different benchmark items found in 4864 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `swe_bench_live:test:conan-io__conan-15699` | 7 | 1.000 | 238 / 238 | `sft-code-swe-rebench-openhands/2389` | 27508 |
| `swe_bench_live:test:conan-io__conan-15931` | 16 | 1.000 | 49 / 49 | `sft-code-swe-rebench-openhands/3506` | 27508 |
| `swe_bench_live:test:streamlink__streamlink-5926` | 67 | 0.996 | 278 / 279 | `sft-code-swe-rebench-openhands/4242` | 27521 |
| `swe_bench_live:test:streamlink__streamlink-5908` | 8 | 0.973 | 358 / 368 | `sft-code-swe-rebench-openhands/2596` | 27521 |
| `swe_bench_live:test:streamlink__streamlink-6242` | 99 | 0.924 | 171 / 185 | `sft-code-swe-rebench-openhands/92` | 27523 |
| `swe_bench_live:test:beeware__briefcase-1638` | 10 | 0.920 | 103 / 112 | `sft-code-swe-rebench-openhands/257` | 27514 |
| `swe_bench_live:test:streamlink__streamlink-6111` | 29 | 0.910 | 264 / 290 | `sft-code-swe-rebench-openhands/54362` | 27521 |
| `swe_bench_live:test:pdm-project__pdm-3393` | 6 | 0.853 | 1587 / 1860 | `sft-code-swe-rebench-openhands/3420` | 27512 |
| `swe_bench_live:test:beeware__briefcase-2075` | 8 | 0.826 | 371 / 449 | `sft-code-swe-rebench-openhands/5499` | 27513 |
| `swe_bench_live:test:beeware__briefcase-2035` | 9 | 0.793 | 219 / 276 | `sft-code-swe-rebench-openhands/14829` | 27513 |
| `swe_bench_live:test:pypsa__pypsa-891` | 20 | 0.760 | 409 / 538 | `sft-code-swe-rebench-openhands/18871` | 27503 |
| `swe_bench_live:test:pdm-project__pdm-2743` | 8 | 0.739 | 345 / 467 | `sft-code-swe-rebench-openhands/2163` | 27511 |
| `swe_bench_live:test:beeware__briefcase-2088` | 10 | 0.671 | 112 / 167 | `sft-code-swe-rebench-openhands/4500` | 27513 |
| `swe_bench_live:test:pdm-project__pdm-3420` | 6 | 0.647 | 306 / 473 | `sft-code-swe-rebench-openhands/36635` | 27511 |
| `swe_bench_live:test:run-llama__llama_deploy-356` | 5 | 0.643 | 220 / 342 | `sft-code-swe-rebench-openhands/2618` | 27523 |

**`sft-code-swe-zero-openhands`**: at least 670 different benchmark items found in 22167 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `swe_bench_live:test:beeware__briefcase-1867` | 3 | 1.000 | 51 / 51 | `sft-code-swe-zero-openhands/6100001056` | 6757 |
| `swe_bench_live:test:conan-io__conan-15699` | 27 | 1.000 | 238 / 238 | `sft-code-swe-zero-openhands/3900004463` | 6752 |
| `swe_bench_live:test:conan-io__conan-15931` | 95 | 1.000 | 49 / 49 | `sft-code-swe-zero-openhands/1300004903` | 6752 |
| `swe_bench_live:test:streamlink__streamlink-5926` | 450 | 0.996 | 278 / 279 | `sft-code-swe-zero-openhands/4700001046` | 6765 |
| `swe_bench_live:test:streamlink__streamlink-5908` | 8 | 0.973 | 358 / 368 | `sft-code-swe-zero-openhands/4400000861` | 6765 |
| `swe_bench_live:test:streamlink__streamlink-6439` | 148 | 0.972 | 413 / 425 | `sft-code-swe-zero-openhands/6100003918` | 6765 |
| `swe_bench_live:test:icloud-photos-downloader__icloud_photos_downloader-1060` | 6 | 0.964 | 319 / 331 | `sft-code-swe-zero-openhands/6100002261` | 6823 |
| `swe_bench_live:test:streamlink__streamlink-6420` | 21 | 0.954 | 352 / 369 | `sft-code-swe-zero-openhands/6200000014` | 6765 |
| `swe_bench_live:test:wireservice__csvkit-1281` | 1 | 0.943 | 477 / 506 | `sft-code-swe-zero-openhands/6300002902` | 6759 |
| `swe_bench_live:test:streamlink__streamlink-6242` | 589 | 0.924 | 171 / 185 | `sft-code-swe-zero-openhands/6100000054` | 6767 |
| `swe_bench_live:test:beeware__briefcase-1638` | 3 | 0.920 | 103 / 112 | `sft-code-swe-zero-openhands/5700000929` | 6758 |
| `swe_bench_live:test:streamlink__streamlink-6111` | 235 | 0.910 | 264 / 290 | `sft-code-swe-zero-openhands/6200003408` | 6765 |
| `swe_bench_live:test:pybamm-team__pybamm-4644` | 3 | 0.909 | 190 / 209 | `sft-code-swe-zero-openhands/6100004917` | 6764 |
| `swe_bench_live:test:streamlink__streamlink-6353` | 336 | 0.904 | 311 / 344 | `sft-code-swe-zero-openhands/6200004054` | 6765 |
| `swe_bench_live:test:pydata__xarray-9974` | 173 | 0.877 | 580 / 661 | `sft-code-swe-zero-openhands/6200000946` | 6757 |

**`sft-dolly-15k`**: at least 4 different benchmark items found in 4 documents (top 4 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `milu:test:18206` | 1 | 0.151 | 8 / 53 | `sft-dolly-15k/5001` | 1325 |
| `milu:test:18158` | 1 | 0.094 | 3 / 32 | `sft-dolly-15k/8241` | 1277 |
| `mmlu:test:5399` | 1 | 0.071 | 4 / 56 | `sft-dolly-15k/903` | 4290 |
| `mmlu:test:3762` | 1 | 0.042 | 2 / 48 | `sft-dolly-15k/6631` | 2232 |

**`sft-indic-aya-collection`**: at least 2 different benchmark items found in 6 documents (top 2 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `heldout_g5_v1:heldout:fw2-hi-test-000022` | 2 | 0.830 | 210 / 253 | `sft-indic-aya-collection/91215` | 223 |
| `in22_gen:test:803` | 4 | 0.011 | 10 / 913 | `sft-indic-aya-collection/31863` | 1702 |

**`sft-indic-aya-dataset`**: at least 10 different benchmark items found in 8 documents (top 10 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `flores200:dev+devtest:dev:mar_Deva:259` | 1 | 1.000 | 8 / 8 | `sft-indic-aya-dataset/166237` | 110 |
| `flores200:dev+devtest:dev:hin_Deva:259` | 1 | 0.650 | 13 / 20 | `sft-indic-aya-dataset/166237` | 334 |
| `flores200:dev+devtest:devtest:hin_Deva:630` | 1 | 0.250 | 2 / 8 | `sft-indic-aya-dataset/52284` | 279 |
| `milu:test:56156` | 1 | 0.240 | 6 / 25 | `sft-indic-aya-dataset/144625` | 120 |
| `milu:test:79035` | 1 | 0.088 | 5 / 57 | `sft-indic-aya-dataset/19493` | 146 |
| `milu:test:35432` | 2 | 0.050 | 5 / 101 | `sft-indic-aya-dataset/16747` | 383 |
| `milu:test:37859` | 2 | 0.041 | 6 / 147 | `sft-indic-aya-dataset/16747` | 416 |
| `milu:test:34937` | 2 | 0.039 | 6 / 155 | `sft-indic-aya-dataset/16747` | 416 |
| `milu:test:76394` | 2 | 0.018 | 1 / 57 | `sft-indic-aya-dataset/27660` | 165 |
| `milu:test:34930` | 2 | 0.009 | 1 / 114 | `sft-indic-aya-dataset/16747` | 437 |

**`sft-indic-indic-align-oasst-t`**: at least 4 different benchmark items found in 9 documents (top 4 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `in22_conv:test:3-2` | 2 | 0.167 | 1 / 6 | `sft-indic-indic-align-oasst-t/7889` | 1430 |
| `in22_conv:test:34-8` | 1 | 0.143 | 1 / 7 | `sft-indic-indic-align-oasst-t/2914` | 1937 |
| `in22_conv:test:40-23` | 1 | 0.091 | 1 / 11 | `sft-indic-indic-align-oasst-t/15521` | 916 |
| `hle:test:672faa45c5a8bce51676ee01` | 5 | 0.002 | 5 / 2298 | `sft-indic-indic-align-oasst-t/13048` | 784 |

**`sft-math-nemotron-math-v2`**: at least 532 different benchmark items found in 60665 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `aime_2025:test:0` | 1 | 0.875 | 7 / 8 | `sft-math-nemotron-math-v2/200994531` | 16477 |
| `bfcl_v3:test:simple_13` | 17 | 0.333 | 1 / 3 | `sft-math-nemotron-math-v2/300586518` | 497 |
| `mmlu:test:1098` | 26 | 0.325 | 26 / 80 | `sft-math-nemotron-math-v2/300802424` | 239 |
| `aime_2025:test:11` | 912 | 0.269 | 18 / 67 | `sft-math-nemotron-math-v2/300025643` | 440 |
| `aime_2025:test:27` | 612 | 0.255 | 13 / 51 | `sft-math-nemotron-math-v2/300228579` | 694 |
| `mmlu:test:4344` | 41 | 0.238 | 5 / 21 | `sft-math-nemotron-math-v2/300544828` | 165 |
| `mmlu:test:4258` | 17 | 0.217 | 5 / 23 | `sft-math-nemotron-math-v2/400497607` | 4652 |
| `mmlu:test:1135` | 38 | 0.188 | 3 / 16 | `sft-math-nemotron-math-v2/300507093` | 173 |
| `aime_2025:test:1` | 1 | 0.185 | 12 / 65 | `sft-math-nemotron-math-v2/200994531` | 20278 |
| `hle:test:6720ff60488fb478b942537b` | 31 | 0.181 | 62 / 343 | `sft-math-nemotron-math-v2/300028639` | 280 |
| `hle:test:66f5fd3235147083021a66c6` | 68 | 0.176 | 13 / 74 | `sft-math-nemotron-math-v2/33614` | 749 |
| `aime_2025:test:7` | 7329 | 0.152 | 7 / 46 | `sft-math-nemotron-math-v2/400001395` | 468 |
| `aime_2025:test:8` | 612 | 0.128 | 6 / 47 | `sft-math-nemotron-math-v2/400041248` | 436 |
| `aime_2025:test:14` | 201 | 0.125 | 4 / 32 | `sft-math-nemotron-math-v2/100097697` | 845 |
| `aime_2025:test:4` | 95 | 0.121 | 4 / 33 | `sft-math-nemotron-math-v2/100082527` | 19930 |

**`sft-math-nemotron-proofs`**: at least 161 different benchmark items found in 2357 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `mmlu:test:4258` | 1 | 0.217 | 5 / 23 | `sft-math-nemotron-proofs/355431` | 7270 |
| `mmlu:test:4409` | 6 | 0.111 | 1 / 9 | `sft-math-nemotron-proofs/1149951` | 23333 |
| `mmlu:test:6857` | 1 | 0.100 | 1 / 10 | `sft-math-nemotron-proofs/1173535` | 2415 |
| `heldout_g5_v1:heldout:owm-test-000009` | 4 | 0.062 | 27 / 437 | `sft-math-nemotron-proofs/767230` | 296 |
| `aime_2025:test:28` | 9 | 0.049 | 2 / 41 | `sft-math-nemotron-proofs/984822` | 274 |
| `hle:test:6715fde1a0465674e6f0bd5a` | 3 | 0.049 | 8 / 162 | `sft-math-nemotron-proofs/718092` | 443 |
| `gaia:2023:27d5d136-8563-469e-92bf-fd103c28b57c` | 12 | 0.043 | 1 / 23 | `sft-math-nemotron-proofs/90265` | 21239 |
| `livecodebench:release_v6:abc372_g` | 4 | 0.043 | 13 / 299 | `sft-math-nemotron-proofs/1023347` | 234 |
| `mmlu:test:4446` | 4 | 0.040 | 2 / 50 | `sft-math-nemotron-proofs/339402` | 38669 |
| `livecodebench:release_v6:abc362_b` | 4 | 0.038 | 6 / 156 | `sft-math-nemotron-proofs/48236` | 418 |
| `mmlu:test:83` | 1 | 0.037 | 2 / 54 | `sft-math-nemotron-proofs/992963` | 1774 |
| `gpqa_diamond:extended:recrs0kUo7Ua1xhKO` | 4 | 0.033 | 5 / 151 | `sft-math-nemotron-proofs/860886` | 342 |
| `livecodebench:release_v6:abc391_f` | 74 | 0.032 | 14 / 434 | `sft-math-nemotron-proofs/1023347` | 234 |
| `mmlu:test:1115` | 4 | 0.032 | 1 / 31 | `sft-math-nemotron-proofs/83569` | 328 |
| `livecodebench:release_v6:abc376_e` | 10 | 0.030 | 7 / 232 | `sft-math-nemotron-proofs/591504` | 1506 |

**`sft-math-nemotron-sft-math-v4`**: at least 377 different benchmark items found in 4776 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `aime_2025:test:11` | 45 | 0.269 | 18 / 67 | `sft-math-nemotron-sft-math-v4/6516` | 432 |
| `hle:test:6720ff60488fb478b942537b` | 3 | 0.181 | 62 / 343 | `sft-math-nemotron-sft-math-v4/14349` | 183 |
| `hle:test:66f5fd3235147083021a66c6` | 5 | 0.176 | 13 / 74 | `sft-math-nemotron-sft-math-v4/510982` | 37907 |
| `mmlu:test:4348` | 1 | 0.167 | 1 / 6 | `sft-math-nemotron-sft-math-v4/40570` | 90857 |
| `hle:test:676433a3921b0ce4e14c557f` | 3 | 0.165 | 36 / 218 | `sft-math-nemotron-sft-math-v4/224103` | 26138 |
| `aime_2025:test:7` | 137 | 0.152 | 7 / 46 | `sft-math-nemotron-sft-math-v4/10585` | 288 |
| `mmlu:test:4258` | 3 | 0.130 | 3 / 23 | `sft-math-nemotron-sft-math-v4/544334` | 7785 |
| `livecodebench:release_v6:2791` | 1 | 0.126 | 47 / 372 | `sft-math-nemotron-sft-math-v4/223273` | 32874 |
| `aime_2025:test:14` | 9 | 0.125 | 4 / 32 | `sft-math-nemotron-sft-math-v4/65308` | 83047 |
| `mmlu:test:4977` | 1 | 0.105 | 2 / 19 | `sft-math-nemotron-sft-math-v4/4383` | 9178 |
| `aime_2025:test:16` | 3 | 0.100 | 1 / 10 | `sft-math-nemotron-sft-math-v4/397447` | 57192 |
| `mmlu:test:6857` | 1 | 0.100 | 1 / 10 | `sft-math-nemotron-sft-math-v4/9701` | 1251 |
| `mmlu:test:4344` | 2 | 0.095 | 2 / 21 | `sft-math-nemotron-sft-math-v4/287992` | 60463 |
| `aime_2025:test:21` | 119 | 0.087 | 4 / 46 | `sft-math-nemotron-sft-math-v4/2337` | 331 |
| `mmlu:test:5219` | 1 | 0.080 | 2 / 25 | `sft-math-nemotron-sft-math-v4/361487` | 11982 |

**`sft-math-openr1-math-raw`**: at least 293 different benchmark items found in 2494 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `mmlu:test:4349` | 1 | 0.481 | 26 / 54 | `sft-math-openr1-math-raw/1400005169` | 166 |
| `mmlu:test:4410` | 1 | 0.462 | 12 / 26 | `sft-math-openr1-math-raw/1400010836` | 67 |
| `mmlu:test:4375` | 1 | 0.391 | 18 / 46 | `sft-math-openr1-math-raw/3800011445` | 68 |
| `bfcl_v3:test:simple_13` | 1 | 0.333 | 1 / 3 | `sft-math-openr1-math-raw/700003475` | 3056 |
| `mmlu:test:4252` | 1 | 0.310 | 9 / 29 | `sft-math-openr1-math-raw/3800011515` | 67 |
| `milu:test:58255` | 1 | 0.250 | 4 / 16 | `sft-math-openr1-math-raw/2000003743` | 3999 |
| `aime_2024:test:60` | 1 | 0.246 | 85 / 345 | `sft-math-openr1-math-raw/3800011332` | 67 |
| `aime_2025:test:8` | 7 | 0.234 | 11 / 47 | `sft-math-openr1-math-raw/1400007666` | 486 |
| `mmlu:test:4258` | 5 | 0.217 | 5 / 23 | `sft-math-openr1-math-raw/9758` | 399 |
| `aime_2024:test:83` | 8 | 0.207 | 41 / 198 | `sft-math-openr1-math-raw/3800011658` | 68 |
| `bfcl_v3:test:multiple_1` | 1 | 0.200 | 1 / 5 | `sft-math-openr1-math-raw/2600002060` | 165 |
| `milu:test:14282` | 3 | 0.188 | 12 / 64 | `sft-math-openr1-math-raw/3100010635` | 670 |
| `bfcl_v3:test:parallel_62` | 4 | 0.167 | 8 / 48 | `sft-math-openr1-math-raw/2000006321` | 1491 |
| `mmlu:test:4348` | 1 | 0.167 | 1 / 6 | `sft-math-openr1-math-raw/1100001251` | 70 |
| `milu:test:14948` | 3 | 0.162 | 11 / 68 | `sft-math-openr1-math-raw/3100010635` | 670 |

**`sft-math-openr1-math`**: at least 238 different benchmark items found in 1803 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `mmlu:test:4349` | 2 | 0.481 | 26 / 54 | `sft-math-openr1-math/1100001792` | 67 |
| `mmlu:test:4410` | 1 | 0.462 | 12 / 26 | `sft-math-openr1-math/1544` | 67 |
| `mmlu:test:4302` | 1 | 0.370 | 20 / 54 | `sft-math-openr1-math/800008252` | 240 |
| `bfcl_v3:test:irrelevance_9` | 1 | 0.333 | 1 / 3 | `sft-math-openr1-math/1400000644` | 4537 |
| `bfcl_v3:test:simple_13` | 1 | 0.333 | 1 / 3 | `sft-math-openr1-math/9358` | 3056 |
| `aime_2025:test:8` | 12 | 0.234 | 11 / 47 | `sft-math-openr1-math/1000004728` | 486 |
| `mmlu:test:4258` | 8 | 0.217 | 5 / 23 | `sft-math-openr1-math/1700008372` | 143 |
| `milu:test:14282` | 1 | 0.188 | 12 / 64 | `sft-math-openr1-math/1621` | 670 |
| `mmlu:test:4348` | 1 | 0.167 | 1 / 6 | `sft-math-openr1-math/800005908` | 70 |
| `milu:test:8917` | 2 | 0.164 | 12 / 73 | `sft-math-openr1-math/900000298` | 326 |
| `milu:test:14948` | 1 | 0.162 | 11 / 68 | `sft-math-openr1-math/1621` | 670 |
| `aime_2025:test:7` | 206 | 0.152 | 7 / 46 | `sft-math-openr1-math/1600006189` | 347 |
| `aime_2025:test:14` | 3 | 0.125 | 4 / 32 | `sft-math-openr1-math/300010116` | 1890 |
| `milu:test:14951` | 1 | 0.125 | 11 / 88 | `sft-math-openr1-math/1621` | 670 |
| `milu:test:17755` | 1 | 0.123 | 8 / 65 | `sft-math-openr1-math/1600009687` | 5266 |

**`sft-oasst2`**: at least 8 different benchmark items found in 5 documents (top 8 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `mmlu:test:5882` | 1 | 0.451 | 107 / 237 | `sft-oasst2/7181` | 969 |
| `mmlu:test:6050` | 1 | 0.439 | 107 / 244 | `sft-oasst2/7181` | 969 |
| `mmlu:test:5857` | 1 | 0.431 | 107 / 248 | `sft-oasst2/7181` | 969 |
| `mmlu:test:5962` | 1 | 0.392 | 107 / 273 | `sft-oasst2/7181` | 969 |
| `milu:test:15661` | 1 | 0.200 | 8 / 40 | `sft-oasst2/8966` | 2153 |
| `milu:test:18206` | 1 | 0.132 | 7 / 53 | `sft-oasst2/5847` | 999 |
| `swe_bench_live:test:kozea__weasyprint-2326` | 1 | 0.004 | 2 / 545 | `sft-oasst2/11303` | 2187 |
| `hle:test:66e932f00bd16d40d4bc4d81` | 1 | 0.003 | 1 / 378 | `sft-oasst2/8809` | 228 |

**`sft-rl-math-openmathreasoning`**: at least 563 different benchmark items found in 65402 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `mmlu:test:4493` | 16 | 0.902 | 111 / 123 | `sft-rl-math-openmathreasoning/1800015574` | 68 |
| `mmlu:test:4291` | 31 | 0.860 | 74 / 86 | `sft-rl-math-openmathreasoning/13800017848` | 67 |
| `mmlu:test:4279` | 16 | 0.855 | 71 / 83 | `sft-rl-math-openmathreasoning/10800019162` | 67 |
| `mmlu:test:4393` | 16 | 0.829 | 58 / 70 | `sft-rl-math-openmathreasoning/2000014723` | 67 |
| `mmlu:test:4423` | 16 | 0.821 | 55 / 67 | `sft-rl-math-openmathreasoning/14300004633` | 67 |
| `mmlu:test:4302` | 32 | 0.778 | 42 / 54 | `sft-rl-math-openmathreasoning/10800017893` | 67 |
| `mmlu:test:4384` | 16 | 0.778 | 42 / 54 | `sft-rl-math-openmathreasoning/9400012772` | 67 |
| `mmlu:test:4263` | 16 | 0.765 | 39 / 51 | `sft-rl-math-openmathreasoning/1700017850` | 67 |
| `mmlu:test:4399` | 16 | 0.745 | 35 / 47 | `sft-rl-math-openmathreasoning/7600011200` | 67 |
| `mmlu:test:4457` | 16 | 0.733 | 33 / 45 | `sft-rl-math-openmathreasoning/12100017196` | 67 |
| `mmlu:test:4350` | 16 | 0.727 | 32 / 44 | `sft-rl-math-openmathreasoning/12100016458` | 67 |
| `mmlu:test:4360` | 16 | 0.692 | 27 / 39 | `sft-rl-math-openmathreasoning/10800021723` | 67 |
| `mmlu:test:4451` | 23 | 0.692 | 27 / 39 | `sft-rl-math-openmathreasoning/9400016462` | 67 |
| `mmlu:test:4460` | 16 | 0.676 | 25 / 37 | `sft-rl-math-openmathreasoning/4800003231` | 67 |
| `mmlu:test:4261` | 16 | 0.657 | 23 / 35 | `sft-rl-math-openmathreasoning/2000011632` | 67 |

**`sft-salesforce-xlam-60k`**: at least 25 different benchmark items found in 182 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `bfcl_v3:test:multiple_65` | 1 | 1.000 | 1 / 1 | `sft-salesforce-xlam-60k/28370` | 2142 |
| `bfcl_v3:test:simple_310` | 1 | 1.000 | 1 / 1 | `sft-salesforce-xlam-60k/27613` | 2676 |
| `bfcl_v3:test:simple_336` | 2 | 1.000 | 1 / 1 | `sft-salesforce-xlam-60k/44060` | 1333 |
| `bfcl_v3:test:simple_379` | 2 | 1.000 | 1 / 1 | `sft-salesforce-xlam-60k/6203` | 2472 |
| `bfcl_v3:test:simple_9` | 7 | 1.000 | 1 / 1 | `sft-salesforce-xlam-60k/541` | 256 |
| `bfcl_v3:test:parallel_18` | 8 | 0.400 | 4 / 10 | `sft-salesforce-xlam-60k/50994` | 1577 |
| `bfcl_v3:test:simple_98` | 10 | 0.333 | 2 / 6 | `sft-salesforce-xlam-60k/39057` | 1413 |
| `milu:test:12344` | 1 | 0.289 | 11 / 38 | `sft-salesforce-xlam-60k/3852` | 1014 |
| `bfcl_v3:test:simple_0` | 3 | 0.200 | 1 / 5 | `sft-salesforce-xlam-60k/39051` | 630 |
| `bfcl_v3:test:parallel_19` | 2 | 0.176 | 3 / 17 | `sft-salesforce-xlam-60k/49274` | 1027 |
| `bfcl_v3:test:parallel_145` | 58 | 0.133 | 4 / 30 | `sft-salesforce-xlam-60k/6934` | 949 |
| `bfcl_v3:test:parallel_multiple_8` | 3 | 0.130 | 3 / 23 | `sft-salesforce-xlam-60k/38963` | 1848 |
| `bfcl_v3:test:simple_133` | 1 | 0.111 | 1 / 9 | `sft-salesforce-xlam-60k/45565` | 867 |
| `bfcl_v3:test:live_parallel_multiple_14-12-0` | 10 | 0.105 | 2 / 19 | `sft-salesforce-xlam-60k/34005` | 1457 |
| `bfcl_v3:test:parallel_multiple_164` | 33 | 0.062 | 6 / 97 | `sft-salesforce-xlam-60k/274` | 2099 |

**`sft-science-glm51-phd`**: at least 9 different benchmark items found in 207 documents (top 9 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `hle:test:6722870ef7bda9406bc723ac` | 2 | 0.014 | 5 / 349 | `sft-science-glm51-phd/23360` | 93359 |
| `hle:test:6700fe18dcd877e17dbc6c26` | 23 | 0.008 | 5 / 601 | `sft-science-glm51-phd/24646` | 11316 |
| `hle:test:66fc56f5d90ebe461bfd0c9c` | 156 | 0.007 | 7 / 1065 | `sft-science-glm51-phd/54631` | 884 |
| `hle:test:6769bce8a4435c3c69035510` | 1 | 0.006 | 7 / 1139 | `sft-science-glm51-phd/73911` | 46536 |
| `hle:test:67253690bcd1c268662e77bb` | 4 | 0.004 | 3 / 769 | `sft-science-glm51-phd/20343` | 32260 |
| `hle:test:676edcd5fc03fd7d07467628` | 5 | 0.002 | 3 / 1915 | `sft-science-glm51-phd/3252` | 49833 |
| `hle:test:6771d50cff6d0a6c35d7ca99` | 1 | 0.002 | 4 / 1725 | `sft-science-glm51-phd/16544` | 12169 |
| `hle:test:66eb707cb1d5bf033573afa3` | 3 | 0.001 | 3 / 2460 | `sft-science-glm51-phd/52594` | 32233 |
| `hle:test:67390213fc9dc4f5102ad835` | 12 | 0.001 | 2 / 2066 | `sft-science-glm51-phd/20387` | 2181 |

**`sft-science-nemotron-science-v2`**: at least 66 different benchmark items found in 286 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `mmlu:test:1421` | 4 | 0.167 | 1 / 6 | `sft-science-nemotron-science-v2/10650` | 320 |
| `milu:test:8418` | 1 | 0.143 | 1 / 7 | `sft-science-nemotron-science-v2/31057` | 4764 |
| `mmlu:test:1470` | 1 | 0.143 | 7 / 49 | `sft-science-nemotron-science-v2/80821` | 231 |
| `mmlu:test:7288` | 1 | 0.095 | 2 / 21 | `sft-science-nemotron-science-v2/47397` | 438 |
| `mmlu:test:7375` | 1 | 0.095 | 2 / 21 | `sft-science-nemotron-science-v2/47397` | 438 |
| `milu:test:14642` | 2 | 0.087 | 4 / 46 | `sft-science-nemotron-science-v2/3023` | 846 |
| `mmlu:test:5219` | 1 | 0.080 | 2 / 25 | `sft-science-nemotron-science-v2/87583` | 2856 |
| `mmlu:test:7306` | 1 | 0.080 | 2 / 25 | `sft-science-nemotron-science-v2/47397` | 438 |
| `mmlu:test:7348` | 1 | 0.080 | 2 / 25 | `sft-science-nemotron-science-v2/47397` | 438 |
| `mmlu:test:7374` | 1 | 0.080 | 2 / 25 | `sft-science-nemotron-science-v2/47397` | 438 |
| `mmlu:test:5403` | 1 | 0.065 | 2 / 31 | `sft-science-nemotron-science-v2/87583` | 2856 |
| `milu:test:15172` | 1 | 0.063 | 4 / 63 | `sft-science-nemotron-science-v2/25763` | 652 |
| `mmlu:test:3078` | 2 | 0.055 | 4 / 73 | `sft-science-nemotron-science-v2/88744` | 203520 |
| `milu:test:11467` | 1 | 0.048 | 1 / 21 | `sft-science-nemotron-science-v2/93322` | 9733 |
| `mmlu:test:5019` | 1 | 0.047 | 2 / 43 | `sft-science-nemotron-science-v2/87583` | 2856 |

**`sft-science-nemotron-science`**: at least 63 different benchmark items found in 369 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `mmlu:test:1421` | 2 | 0.167 | 1 / 6 | `sft-science-nemotron-science/86581` | 320 |
| `mmlu:test:1470` | 1 | 0.143 | 7 / 49 | `sft-science-nemotron-science/50243` | 219 |
| `mmlu:test:7288` | 3 | 0.095 | 2 / 21 | `sft-science-nemotron-science/14799` | 306 |
| `mmlu:test:7375` | 3 | 0.095 | 2 / 21 | `sft-science-nemotron-science/14799` | 306 |
| `milu:test:14642` | 2 | 0.087 | 4 / 46 | `sft-science-nemotron-science/65764` | 846 |
| `mmlu:test:7306` | 3 | 0.080 | 2 / 25 | `sft-science-nemotron-science/14799` | 306 |
| `mmlu:test:7348` | 3 | 0.080 | 2 / 25 | `sft-science-nemotron-science/14799` | 306 |
| `mmlu:test:7374` | 3 | 0.080 | 2 / 25 | `sft-science-nemotron-science/14799` | 306 |
| `milu:test:19498` | 1 | 0.068 | 4 / 59 | `sft-science-nemotron-science/33738` | 56350 |
| `milu:test:19813` | 1 | 0.067 | 4 / 60 | `sft-science-nemotron-science/33738` | 56350 |
| `milu:test:15172` | 1 | 0.063 | 4 / 63 | `sft-science-nemotron-science/104153` | 652 |
| `milu:test:20141` | 1 | 0.056 | 2 / 36 | `sft-science-nemotron-science/33738` | 56350 |
| `milu:test:20151` | 1 | 0.053 | 2 / 38 | `sft-science-nemotron-science/33738` | 56350 |
| `mmlu:test:7326` | 2 | 0.053 | 1 / 19 | `sft-science-nemotron-science/16853` | 2578 |
| `milu:test:10786` | 1 | 0.050 | 4 / 80 | `sft-science-nemotron-science/33738` | 56350 |

**`sft-stem-code-openthoughts3`**: at least 471 different benchmark items found in 7457 documents (top 15 by coverage; the checker lists the best 5 items per document, so this is a lower bound)

| Benchmark item | Documents | Highest coverage | Shared runs / item runs | Example document | Offset |
|---|---:|---:|---:|---|---:|
| `milu:test:15749` | 8 | 0.347 | 35 / 101 | `sft-stem-code-openthoughts3/11600009558` | 420 |
| `milu:test:17670` | 10 | 0.343 | 35 / 102 | `sft-stem-code-openthoughts3/11600009558` | 420 |
| `milu:test:8199` | 25 | 0.256 | 23 / 90 | `sft-stem-code-openthoughts3/11600009558` | 420 |
| `milu:test:8201` | 23 | 0.247 | 23 / 93 | `sft-stem-code-openthoughts3/11600009558` | 420 |
| `milu:test:8200` | 23 | 0.245 | 23 / 94 | `sft-stem-code-openthoughts3/11600009558` | 420 |
| `mmlu:test:4258` | 6 | 0.217 | 5 / 23 | `sft-stem-code-openthoughts3/7000009013` | 34066 |
| `bfcl_v3:test:simple_98` | 1 | 0.167 | 1 / 6 | `sft-stem-code-openthoughts3/4400007659` | 50452 |
| `milu:test:19953` | 1 | 0.167 | 1 / 6 | `sft-stem-code-openthoughts3/1300001147` | 6348 |
| `milu:test:9157` | 2 | 0.167 | 1 / 6 | `sft-stem-code-openthoughts3/700002862` | 4208 |
| `milu:test:8643` | 3 | 0.163 | 8 / 49 | `sft-stem-code-openthoughts3/11600002217` | 9324 |
| `aime_2025:test:14` | 21 | 0.125 | 4 / 32 | `sft-stem-code-openthoughts3/4900002690` | 295 |
| `aime_2025:test:3` | 1 | 0.118 | 2 / 17 | `sft-stem-code-openthoughts3/10400008274` | 386 |
| `gaia:2023:2b3ef98c-cc05-450b-a719-711aee40ac65` | 12 | 0.110 | 13 / 118 | `sft-stem-code-openthoughts3/500002679` | 2546 |
| `milu:test:9042` | 14 | 0.100 | 9 / 90 | `sft-stem-code-openthoughts3/11700004442` | 420 |
| `milu:test:11230` | 11 | 0.091 | 9 / 99 | `sft-stem-code-openthoughts3/11700004442` | 420 |

Coverage is the share of the item's runs found in the document. A value near 1.0 is a full copy; a low value is a short shared passage, for example a common problem statement. The ids above are enough to find the document in the set; the item text stays in Team 9's restricted folder.

## 5. Checks

| Check | Sets passed |
|---|---:|
| `all_source_files_converted` | 15 of 30 |
| `canary_ids_in_input` | 30 of 30 |
| `canary_scan_complete` | 30 of 30 |
| `clean_file_flags_0` | 30 of 30 |
| `docs_match_checker` | 30 of 30 |
| `every_removed_row_is_hit` | 1 of 30 |
| `flagged_count_matches` | 30 of 30 |
| `flagged_ids_in_input` | 30 of 30 |
| `ids_disjoint_across_units` | 15 of 30 |
| `ids_unique` | 30 of 30 |
| `parts_cover_all_converted_rows` | 15 of 30 |
| `rows_in_eq_kept_plus_removed` | 30 of 30 |

`rows_in_eq_kept_plus_removed`: rows in = rows kept + rows removed. `clean_file_flags_0`: the checker, run again on the clean file, flags 0 of the kept rows. `canary_scan_complete`: `canary_scan.py` read every file (exit 0 or 1). A set with a failed check or a canary is not in this report (the script stops).

## 6. Inputs (to reproduce a run)

| Set | Input file | Bytes | sha256 |
|---|---|---:|---|
| `sft-agentic-nemotron-agentic-v1` | `agentic-nemotron-agentic-v1.jsonl` | 5,500,570,007 | `5cca4abb9ead609776b4b4f2df99c7d2a95d27f0dcca0137ec1504a57680d0ec` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0000.jsonl` | 300,000,898 | `da8af19ac90c53b9edae0d147caf17e10bbcb6edf11bb0072cc222a3efa90334` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0001.jsonl` | 300,029,931 | `fb0a3bce896541d4196a868eb7670514052c04c5f19d60e4990b1ad9b5e6eefa` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0002.jsonl` | 300,008,031 | `1eab45d5e748304d4f6c0150e92a1da9c0cdd97967947d393967a1dba7c3fca5` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0003.jsonl` | 300,012,764 | `dcf4b3156f3e5033af64ea27a02e5818f8100258ea6f8aec038c6950d13934e2` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0004.jsonl` | 300,012,600 | `96a1abc61c2b8d0bed464070d3d48ce7df0dd8323a7e09d79d58351184437e1f` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0005.jsonl` | 300,032,657 | `d1815f05e6f1a1331ad56952ba5fe1c9f3c20fa20291cd281a5765995a6c3805` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0006.jsonl` | 300,009,738 | `83e6dd9f7d42a0aab68cec46cfab9f792c72c78b46455fa245b36f6f6d284b2b` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0007.jsonl` | 300,001,752 | `4287506496fac10ba7ec108ec22d8b811e7c39026fe9fc7f97a4749d041e992b` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0008.jsonl` | 300,023,451 | `9b86c032a99a98b76f98314b3bac63aa1a9f8252101287ad29f119126800dbb3` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0009.jsonl` | 300,016,600 | `51b2ce25cc46d11bd3678c20ee92ec8eefb78217a342762f901777904b5ebe23` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0010.jsonl` | 300,014,446 | `51ebd7061c9f54c24898c45030f1c1a88db6d0c32a68c286575154f12813c8bc` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0011.jsonl` | 300,109,260 | `fe61d673c33884c9b159d440216649444ec6aef97f5a6d5e354c812b27ad7129` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0012.jsonl` | 300,009,216 | `e27c6c9e9192fb9efd5aa1bcd87bd849b069775845fa87ad4662fdbd60afc8ef` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0013.jsonl` | 300,032,160 | `6d75728201dcc1221144a0f37e9cdde42f54d06dd6b58a6d2ec123e6e466c03a` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0014.jsonl` | 300,011,788 | `e4fd7bb0fb43fedb5a0ae3979a48c113aa8ed5d537981d68fe9053f78d6028e7` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0015.jsonl` | 300,005,449 | `01b8e97c5f1bb79e534c254863b1a7c6044f130311ab3103c7986cc30c10760c` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0016.jsonl` | 300,036,346 | `7e1f81fab0a3a03311c7a759fd6231164b6d20e6f6131e3eb551ff7e771fc3b3` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0017.jsonl` | 300,010,974 | `a7b16dc466426ddf2e9b6ba1c5beada973cd6b8c56841e562fd4a2e30ec26b17` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0018.jsonl` | 300,008,035 | `14f0b03fcf3b145b236f01fe16d7c6fd68f1b60dc6591843a53830c8557509d1` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0019.jsonl` | 300,003,968 | `4e1dc7bec9ee3d4b4bfba210d9cb79d7b2347f2215c1906aad7ba3debcde0833` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0020.jsonl` | 300,039,366 | `7b187ebecf4843f3af7051829d78f72eeeee7fcaef9150833c9035ebf56c1869` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0021.jsonl` | 300,012,781 | `3dd607b9725abf422c299a1ae95972f5175aca0742f718503379918287fef237` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0022.jsonl` | 300,065,466 | `98c6a5c86f4ba8a3925845678395b8c07037d470cd080ed836f2be9fe78c3707` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0023.jsonl` | 300,018,665 | `c22b95fd8f6e81d6da75400648d66c768c21445dcb18110b8af0c2fccd541cce` |
| `sft-agentic-nemotron-sft-agentic-v2-tool-calling` | `u000.part0024.jsonl` | 277,728,019 | `cf3dc93001dccf1d2c55b3ed6ae04c71de746c5e21781feb46eff62c2d002790` |
| `sft-bespoke-stratos-17k` | `bespoke-stratos-17k.jsonl` | 298,311,597 | `55f7d082ceb9a5df726a20f28b4bdecf07bc4c1b9471b264313f80adc48a2d74` |
| `sft-chat-nemotron-if-v1` | `chat-nemotron-if-v1.jsonl` | 95,149,354 | `1fdd7943eed071e4b0d942b987b1e87d63b8d16a65be5f36d81f99219681b12d` |
| `sft-chat-nemotron-if-v2` | `u000.part0000.jsonl` | 300,014,364 | `e606823d258bb9879c47d7baa0a002f5286170d53f930f8a7e868bb481efb610` |
| `sft-chat-nemotron-if-v2` | `u000.part0001.jsonl` | 300,013,899 | `8aec878469ff050aa42c784e2d82a0eb8bcda5c00133cb87e083b3e4687ef45e` |
| `sft-chat-nemotron-if-v2` | `u000.part0002.jsonl` | 300,000,187 | `7818a24c5780303ba5d604aa9e4bb4f248bd289ce81b97bd95b9f21709f65e31` |
| `sft-chat-nemotron-if-v2` | `u000.part0003.jsonl` | 300,019,724 | `da2651c873dd76a31992edd58ae257004d5d029bceda14ce3820be406e12794f` |
| `sft-chat-nemotron-if-v2` | `u000.part0004.jsonl` | 300,003,157 | `8490f6aff370d410928bb0155dc7ed23abce00660468339d4a422aa36e1c21f5` |
| `sft-chat-nemotron-if-v2` | `u000.part0005.jsonl` | 300,001,379 | `f245f37a1add15c1759f13ecf38577ce960a514d1c5643b0e7f42cbfc50e3fa0` |
| `sft-chat-nemotron-if-v2` | `u000.part0006.jsonl` | 300,009,291 | `713044762365a342f8dbd6d132b5865c48e16522fb962da2cb02e3e3e1c93309` |
| `sft-chat-nemotron-if-v2` | `u000.part0007.jsonl` | 300,006,731 | `df23296a3141290046ecabf30d6e872c241417bd85dbbc99774159a53a188ff5` |
| `sft-chat-nemotron-if-v2` | `u000.part0008.jsonl` | 300,010,472 | `e6dc824f7013f9f929a428707cc5995f619683d8bb0e2496fbd2ff5efdb6aee0` |
| `sft-chat-nemotron-if-v2` | `u000.part0009.jsonl` | 300,004,203 | `736cf09485ecd2e8a5c40ce5082e8f7bde84abad940a656271b6f3abd8d4d2b2` |
| `sft-chat-nemotron-if-v2` | `u000.part0010.jsonl` | 300,017,404 | `e7a85f5a636e92cf0c0575ccad570f0979ea63eb4442a872c2fc5482d1d704a0` |
| `sft-chat-nemotron-if-v2` | `u000.part0011.jsonl` | 300,006,205 | `6036ffccc6f3ae366a7c724619a977c6c07e16cb4a7099246e430924c253a08b` |
| `sft-chat-nemotron-if-v2` | `u000.part0012.jsonl` | 300,027,489 | `41018713bddad85e28531d17caf60281b9b6dba2232ac12673b8a6c5bfb43078` |
| `sft-chat-nemotron-if-v2` | `u000.part0013.jsonl` | 300,007,113 | `e2e01df0fb0bf2c5635fa5f73b14425dc9eaff4229f50535d59287f9d2e8ffd1` |
| `sft-chat-nemotron-if-v2` | `u000.part0014.jsonl` | 300,016,662 | `573cb0e79541e53a6d0bd53ee36ea008828b8a93cd032f3b049b92e0b99c5f43` |
| `sft-chat-nemotron-if-v2` | `u000.part0015.jsonl` | 300,001,399 | `4e16f0c4494023848bb6a188f7c1fd635cc2e350ad0bdecbbab70e0b4bafb754` |
| `sft-chat-nemotron-if-v2` | `u000.part0016.jsonl` | 300,003,569 | `bcc60335b49fb5ab40b0bac6606017a2a2f5c16c2792262d79590f1962d6649d` |
| `sft-chat-nemotron-if-v2` | `u000.part0017.jsonl` | 300,006,470 | `8251e1f4c74e40dd8f5ed2efad45522f9dc34c2650476dce19a10901ca770c24` |
| `sft-chat-nemotron-if-v2` | `u000.part0018.jsonl` | 300,000,345 | `9a802baae305621c261007628b21d2d2c0bd0a8783b96d6f8c4dd173c68c9d98` |
| `sft-chat-nemotron-if-v2` | `u000.part0019.jsonl` | 300,005,535 | `a31755998905737bca545118de55008290f9d35b10abe522c43dcd4cb68abcb8` |
| `sft-chat-nemotron-if-v2` | `u000.part0020.jsonl` | 300,003,235 | `7753ab3f86c674e33afd19782bc926fa2103e8e4f595e46b6d2f3584a61ec602` |
| `sft-chat-nemotron-if-v2` | `u000.part0021.jsonl` | 300,016,133 | `944e7e15a4568f23554079b8c2411df181b465027117b988e61c8edc92836d34` |
| `sft-chat-nemotron-if-v2` | `u000.part0022.jsonl` | 300,001,550 | `f56edab0a612b1b1277f578eb87f34c6749a6dcccbc845188a0711d11a40d860` |
| `sft-chat-nemotron-if-v2` | `u000.part0023.jsonl` | 300,012,232 | `6dceb2e78f6c72c8f3089019561d386402e2dcb7ce28dc594343bab267ea9efc` |
| `sft-chat-nemotron-if-v2` | `u000.part0024.jsonl` | 300,000,277 | `aac91f03e734c5ed25a647c420965ed429719904d655e930818ce7f6b91ad504` |
| `sft-chat-nemotron-if-v2` | `u000.part0025.jsonl` | 300,000,666 | `3248db4f273b00110f8f0d0c4688f7c68be0cc66617184877801bd26ce712afa` |
| `sft-chat-nemotron-if-v2` | `u000.part0026.jsonl` | 300,006,425 | `c71055f6653cc67cbe6e37c9380e69b1d436c71b18449be7080c68ae2e2025cf` |
| `sft-chat-nemotron-if-v2` | `u000.part0027.jsonl` | 300,006,699 | `0c9b10b713d6ec837d862df377621e023dd1335eb99d03a25b29c34c0fcc7372` |
| `sft-chat-nemotron-if-v2` | `u000.part0028.jsonl` | 300,001,716 | `8506046b6cb766822608cf425ae708efc635fdc378cad79a9d84c20b00349ffd` |
| `sft-chat-nemotron-if-v2` | `u000.part0029.jsonl` | 300,006,714 | `ee6612587d27b6f6f50d2da17c0e2e7e8f9d243d2523c546f98cbbf8800bd04f` |
| `sft-chat-nemotron-if-v2` | `u000.part0030.jsonl` | 300,000,317 | `812cb586ddcff098fbcdbb2039a31ae0d175cb0dfc32863a00d5aebccb9f2b33` |
| `sft-chat-nemotron-if-v2` | `u000.part0031.jsonl` | 300,008,024 | `f612bd57f8daf3c7c226eeb834f0007f6f11613883ffc7bcf782a38104048446` |
| `sft-chat-nemotron-if-v2` | `u000.part0032.jsonl` | 300,007,472 | `d6b32d5c1ef0ab9bf3f97cfa51bdc472ab64357e5de390d7f1c5191de88aee4d` |
| `sft-chat-nemotron-if-v2` | `u000.part0033.jsonl` | 240,681,203 | `678489bb8031b72549e4ff2c211b3335c7f729c70f32bf366e9acbef0e265a40` |
| `sft-code-codeforces-cots` | `code-codeforces-cots.jsonl` | 2,287,612,938 | `d3ef4f33f43f1d22c2912fe2de97951d3c44843e20994b9b24b711f635c0e2fa` |
| `sft-code-nemotron-cascade-swe` | `u001.part0000.jsonl` | 300,031,511 | `4a9b2c58c49b9f59cd1c5e90f4022f889eebdd352a5e0d91dbacbcd0666235f6` |
| `sft-code-nemotron-cascade-swe` | `u000.part0000.jsonl` | 300,009,446 | `23468d927ee37b0bad463264a1f7b5fd99c90398c776b62f749399dc98267b13` |
| `sft-code-nemotron-cascade-swe` | `u001.part0001.jsonl` | 300,043,968 | `e7e94b9acec08c3d985ff40f042fafd7ea7671e4ace532611bcd635dfc24f244` |
| `sft-code-nemotron-cascade-swe` | `u002.part0000.jsonl` | 300,009,836 | `0d0c80952234abc2c59a6b7ecf2a90a66a079228356ca9e7978e560219fa456d` |
| `sft-code-nemotron-cascade-swe` | `u000.part0001.jsonl` | 300,063,589 | `e0e3dae3c9e2dbf610cb5c60427b16e640c3a56e9ff72002eb9cc3610f242f78` |
| `sft-code-nemotron-cascade-swe` | `u002.part0001.jsonl` | 300,007,682 | `c2d6152f5a733e22fde4308b0b4a4a8e65d37bae48d01e39a7b7c793af57cd6d` |
| `sft-code-nemotron-cascade-swe` | `u001.part0002.jsonl` | 300,035,081 | `9b2777b17377fb8300b13e9c8b795f389ad14fe64b39a04abe67e76d3cebb62f` |
| `sft-code-nemotron-cascade-swe` | `u000.part0002.jsonl` | 300,017,427 | `7b0af8b5b8d24afd5177cd4746dda8fd57e151dd65130a3d4cf3a6b97c4898e0` |
| `sft-code-nemotron-cascade-swe` | `u002.part0002.jsonl` | 256,322,858 | `565853dc9e9142d21e5c7a16ff06394824d4d15860edb4a9116eb1b8629b9eb3` |
| `sft-code-nemotron-cascade-swe` | `u001.part0003.jsonl` | 300,016,350 | `e4889663a91df29bbcc817b06b177157c43433019c0101f913a7242022807448` |
| `sft-code-nemotron-cascade-swe` | `u000.part0003.jsonl` | 300,008,451 | `d791eb18b877ea455bcc9e50f72d28c03a606351866be5356a6dc64f52777dc8` |
| `sft-code-nemotron-cascade-swe` | `u001.part0004.jsonl` | 300,000,441 | `cbe66728920ef74585c9b796c3a7874cc7b7871c3f3bb9d1d933b433f5dc2718` |
| `sft-code-nemotron-cascade-swe` | `u000.part0004.jsonl` | 300,010,798 | `36477cec7d7024629e17a953b912e0de1725db0323da65e9a957336e3f3bcaa0` |
| `sft-code-nemotron-cascade-swe` | `u001.part0005.jsonl` | 300,041,399 | `a04d36ac1233899e1466c5591601226e2e199534feab35b77df24f9beb80e1be` |
| `sft-code-nemotron-cascade-swe` | `u001.part0006.jsonl` | 300,004,701 | `d4decb5f51c9d86979c0730cfdcd8d6b7f10aee3cbba7949baedebed4147a763` |
| `sft-code-nemotron-cascade-swe` | `u000.part0005.jsonl` | 300,006,220 | `ccd1a900fc03fbb434bb1cca351577fe228e35359acf0ac7c2cf7f875c900d1a` |
| `sft-code-nemotron-cascade-swe` | `u001.part0007.jsonl` | 300,029,939 | `d8e4fc3d1ab47cc301083c0eed3077dfc273b3d0e7416457b0563deaf19175c0` |
| `sft-code-nemotron-cascade-swe` | `u000.part0006.jsonl` | 300,015,093 | `ce04f8dceb2ffa7fd383588b6f5375eb176eeaf092c4c72d776bf6cc8c50191a` |
| `sft-code-nemotron-cascade-swe` | `u001.part0008.jsonl` | 300,002,795 | `2e7c0f6f84f18513ebfc13b1005e6148dbec2aed7bfe46418a760cd686639605` |
| `sft-code-nemotron-cascade-swe` | `u000.part0007.jsonl` | 67,028,164 | `8fc73cbb6c96b2e3b485f42efc30a2a7af2c8428364ce1f9886ef529e184ed8b` |
| `sft-code-nemotron-cascade-swe` | `u001.part0009.jsonl` | 300,006,344 | `8e10b3aa2d657d194add7f604b77713cfb33b8123b8c67d63a85295e99daf19a` |
| `sft-code-nemotron-cascade-swe` | `u001.part0010.jsonl` | 300,035,292 | `bd86016017d5ad2b7bc84a1f5ce1f19fdc8fc03585355e3a53646f2b2a4e928f` |
| `sft-code-nemotron-cascade-swe` | `u001.part0011.jsonl` | 300,042,460 | `c7f4d3a92eef520e9da5c0827ca0b4a432872aaf548e7469db4540ce59cf4837` |
| `sft-code-nemotron-cascade-swe` | `u001.part0012.jsonl` | 147,382,344 | `98201ed0fa4c93631122197a1fbc02351ee329d58cd618d84b7769abb0b18d37` |
| `sft-code-nemotron-cuda` | `code-nemotron-cuda.jsonl` | 82,578,942 | `af858d047eb12146110c7bb815e1814248faac6d439549d8482a8747bdcace6c` |
| `sft-code-nemotron-opencode` | `u000.part0000.jsonl` | 300,027,436 | `f199e01ab57e50834def8797c7deaf062bda3d13a987a9e77874d8b9b5b942fc` |
| `sft-code-nemotron-opencode` | `u000.part0001.jsonl` | 300,003,280 | `a4fde85ca5b3322f13233cc755bdcf375449d9bbfdb0a00c3715f97deeae1b3f` |
| `sft-code-nemotron-opencode` | `u000.part0002.jsonl` | 300,055,130 | `a4237a852a0f63d9c7db7ecba7b114b3c934e052e64111e03a1954f83e889489` |
| `sft-code-nemotron-opencode` | `u000.part0003.jsonl` | 300,142,037 | `14a55f5b32c65d4175fc242afafb78259c588d25ecf5f085831ce63b08cfefdb` |
| `sft-code-nemotron-opencode` | `u000.part0004.jsonl` | 300,107,147 | `f5b7ba091f7d8a132d3420288256429ecc8e3f31353c1f6025c1c754ac8bf931` |
| `sft-code-nemotron-opencode` | `u000.part0005.jsonl` | 300,042,014 | `8ecd0529c3dca75acd5c16d80364910f46dbdb4bf195d92aae5710ce1c82d560` |
| `sft-code-nemotron-opencode` | `u000.part0006.jsonl` | 300,023,240 | `48f1d8edc45534db459f74fc64ddd44c40aafb832517652a73bcfd22f7564f53` |
| `sft-code-nemotron-opencode` | `u000.part0007.jsonl` | 300,055,840 | `dac3f0d1f5e32502aaf9bb2b0a90c6980520a1dcd2c76345d7bbf37220452b81` |
| `sft-code-nemotron-opencode` | `u000.part0008.jsonl` | 300,006,626 | `079672017395652515c59862297a7b3eadf570bf77402845e0cb0698aa31adc4` |
| `sft-code-nemotron-opencode` | `u000.part0009.jsonl` | 300,049,132 | `c012434addd2fbf5ed430e4fc82e4466ff404498edbb802aba80cb41f45c7673` |
| `sft-code-nemotron-opencode` | `u000.part0010.jsonl` | 300,009,665 | `d6bc1a5ef7952d4747afaec7df0c7c558407535352cde7361bcd710be87427d3` |
| `sft-code-nemotron-opencode` | `u000.part0011.jsonl` | 300,061,542 | `7fcbdfaacc0e51cc6d7ab62b54ccc2ca9e8760b54a1f322dab5b037eb6ad5a72` |
| `sft-code-nemotron-opencode` | `u000.part0012.jsonl` | 300,180,450 | `0a95ac019c14f3187cc7efca02dce59890a94e2fb40361892653a0c4f5577f7e` |
| `sft-code-nemotron-opencode` | `u000.part0013.jsonl` | 300,002,540 | `049188c4b5ad3b05d7807480498cb11e343b5a7e5cb6f2e1c9f0c798ef773512` |
| `sft-code-nemotron-opencode` | `u000.part0014.jsonl` | 300,114,273 | `e69f30651e4a99128c034f26830e5fe9580013e7bd8e09891f85ca0f67958ed1` |
| `sft-code-nemotron-opencode` | `u000.part0015.jsonl` | 300,033,847 | `c7e35dc81fcea3f8a3e966466a985dcd043d89d9970bda8520c809c62e83d8a7` |
| `sft-code-nemotron-opencode` | `u000.part0016.jsonl` | 300,012,474 | `d89c6666fa5cef7de819890a21cfa45ff90ddefe4a18ea13f1ffd5c0e82e18b1` |
| `sft-code-nemotron-opencode` | `u000.part0017.jsonl` | 300,037,260 | `d51c415a6240072ea57664c86d81f60fc1e19e8c2f6d9a7000d02c0c7732bd32` |
| `sft-code-nemotron-opencode` | `u000.part0018.jsonl` | 300,136,923 | `780a321855b49a543424510e0e5339b66d3769a33ac76a30535e5b42b03187f7` |
| `sft-code-nemotron-opencode` | `u000.part0019.jsonl` | 300,084,880 | `860ae3a0df4a3ecf64eb720e45e4f7927a1f07e9ee62d3f1321f20e01ea97e53` |
| `sft-code-nemotron-opencode` | `u000.part0020.jsonl` | 247,859,056 | `f402b34105e68b9bcfa5e12edee42f4f3f1cc16cde12f975493852e5a224b067` |
| `sft-code-nemotron-terminal` | `code-nemotron-terminal.jsonl` | 2,231,536,740 | `445c53c776d693214ab7fdf73e8ebdc1e17430a95584f1d3d8a57631226056f5` |
| `sft-code-opencodereasoning` | `u027.part0000.jsonl` | 300,012,540 | `0e4a528b6e975384362e7baf31e47f1ddebdf0d94979f70021ca49930a3810e8` |
| `sft-code-opencodereasoning` | `u027.part0001.jsonl` | 300,001,966 | `0acd4bb64538aeb61894f7055325189a3947f788977d68f3621908c25273ef9d` |
| `sft-code-opencodereasoning` | `u027.part0002.jsonl` | 300,004,178 | `cf5c1f4d2251c47c9be833e9898296b4475a28b6e9997958ef4481da67766fc7` |
| `sft-code-opencodereasoning` | `u027.part0003.jsonl` | 31,412,454 | `768ac93a55a943fd9d26f32b270bcc5bdf90cd66d40244f3db998e8c9be2b245` |
| `sft-code-opencodereasoning` | `u026.part0000.jsonl` | 300,010,251 | `278c4fcccd5e087f9295a1e740ef932d479d805e7b43a6f419e8e864f6ab0c69` |
| `sft-code-opencodereasoning` | `u020.part0000.jsonl` | 300,027,650 | `88dfe3ed4d56a8575cb0babdaad65f92a70efe1cfae4649fa20855fa7fe7bc5b` |
| `sft-code-opencodereasoning` | `u026.part0001.jsonl` | 300,002,889 | `f6c37dc8f7f46329a502927c062a15e07a87fdb52a9d016795cf7f4eb9faf2cb` |
| `sft-code-opencodereasoning` | `u020.part0001.jsonl` | 300,030,648 | `fa84a355413f411270d32328c62fdb91ef15ecc1667cfa3915649a4b6cf896fe` |
| `sft-code-opencodereasoning` | `u020.part0002.jsonl` | 175,058,409 | `7175cbfafaf8afb32677a6314f17d30cc66b2c1467854884c1aea00c91944ca1` |
| `sft-code-opencodereasoning` | `u026.part0002.jsonl` | 300,018,454 | `2452b911a62f062d3daf85eb102da11d376480e7afbe4b57015be9289f15b335` |
| `sft-code-opencodereasoning` | `u026.part0003.jsonl` | 31,597,822 | `48f59160c5801e9706a5425ecddac3b83184cb74bdc37a9c5cb302f8b28d6b6d` |
| `sft-code-opencodereasoning` | `u021.part0000.jsonl` | 300,038,045 | `f4666f84d3c8fb581d755750f865caf891a2a6a56f26cfd11ea7f5807314d7c1` |
| `sft-code-opencodereasoning` | `u021.part0001.jsonl` | 300,052,635 | `b03b4a98b4035486ff6edc6ff5655a6254b1750694f195b77073e5b1d63a4ad3` |
| `sft-code-opencodereasoning` | `u028.part0000.jsonl` | 300,053,018 | `82163a472a0b3228278cb2d9fd80f3eccc9a4d487ad1c468116c06accb21c567` |
| `sft-code-opencodereasoning` | `u021.part0002.jsonl` | 300,048,483 | `22192bcaa8aec11f53cb5de0de9b894ab161a3525d31c129afc85ce0121fa794` |
| `sft-code-opencodereasoning` | `u021.part0003.jsonl` | 34,699,895 | `e48d0d059835626fac62ae4ac6ca71465ad8a64ea8cfc12c39d6c1ef8f199d9f` |
| `sft-code-opencodereasoning` | `u028.part0001.jsonl` | 300,019,940 | `797d2545035bf7d4e56defd0dbcb9ce63ff6b5c925a2ed5bb402a807e4147436` |
| `sft-code-opencodereasoning` | `u023.part0000.jsonl` | 300,042,729 | `b10bbd01b02e2ec43d555abde813757ac9ee3d55c69d7cf55fbc36cd828d21f9` |
| `sft-code-opencodereasoning` | `u022.part0000.jsonl` | 300,013,679 | `13c6adb6b27588e7c6f22c9b06f4b8f6cca6ad475bc6ceb8b641ad20d540f64c` |
| `sft-code-opencodereasoning` | `u029.part0000.jsonl` | 300,021,393 | `2de9562e53c26567adf182006fbafe7611e79ba829725cd568607fc0bb61746f` |
| `sft-code-opencodereasoning` | `u028.part0002.jsonl` | 300,051,640 | `3df7fb09f988d8a2d5a4309a856b641c1d743f3f0b14f5df2e8297d699b87393` |
| `sft-code-opencodereasoning` | `u028.part0003.jsonl` | 27,515,709 | `0a8d450390ea3dac3bf0239a18f1e09194ac3a03650c3d4fa7188ee1e45f052f` |
| `sft-code-opencodereasoning` | `u023.part0001.jsonl` | 300,008,115 | `a95bda702da23318cd94a495457fcf2d3f146832fb13e7caa24344309f15cb2b` |
| `sft-code-opencodereasoning` | `u022.part0001.jsonl` | 300,035,380 | `f007b77e32700c135f3fc0fd84e3c5e7c72a0d7a54368d941cdee018f5b103c6` |
| `sft-code-opencodereasoning` | `u029.part0001.jsonl` | 300,050,786 | `ed5870eb651a2c4038bfca130599f6fc9846656487ef1ff7b2c5b7a7ccd68f51` |
| `sft-code-opencodereasoning` | `u023.part0002.jsonl` | 178,492,709 | `3c0355152aac9d5dc6aa4c23726eb4eae380a41f120473157ddfd4e206ded6a2` |
| `sft-code-opencodereasoning` | `u022.part0002.jsonl` | 300,015,686 | `fe08d2f60a3594436b0a928bb3058218626da67b30a305545e74bf5dd7ea0e9b` |
| `sft-code-opencodereasoning` | `u022.part0003.jsonl` | 33,410,048 | `10d5b4c6bb80744643eff36108b9ad59a3c0af9f0c0e4b4c94136d1d96cb6557` |
| `sft-code-opencodereasoning` | `u029.part0002.jsonl` | 300,011,763 | `854eeff90d55d0c2846f80eae3c4aee155d196cd3f64c744d2979b78e8b93057` |
| `sft-code-opencodereasoning` | `u029.part0003.jsonl` | 28,153,451 | `2138b87160628ff04d5e5180e00012dc7caaa68c51cfe59d50a382c8fc0d9604` |
| `sft-code-opencodereasoning` | `u025.part0000.jsonl` | 300,040,333 | `e569ffb8c3e27c9ba70ad57c24487c3e522e13b2fed585cf2cadb119568db1d8` |
| `sft-code-opencodereasoning` | `u025.part0001.jsonl` | 300,025,829 | `ee1c06dabc9081257a43416419a28156b4dad00c0a513d0f3d94f24c2de1a451` |
| `sft-code-opencodereasoning` | `u025.part0002.jsonl` | 7,413,040 | `f403a84dadf63fd470156caa8b20f2d6d5a9d8769d4bff4f417599cb03507495` |
| `sft-code-opencodereasoning` | `u007.part0000.jsonl` | 300,006,622 | `793be240cae2448058027ec52081c65566a47d868baed67f55af2ed3eb9a3397` |
| `sft-code-opencodereasoning` | `u014.part0000.jsonl` | 300,016,589 | `4f51f0f4ce119ba97e39794d96ebab9609150760058e439e345c2457dcd02587` |
| `sft-code-opencodereasoning` | `u015.part0000.jsonl` | 300,002,468 | `f3b3a0b47a86509d068e6c919bd1aab64f3aa5223e1d2f065d46f2f9173ffc06` |
| `sft-code-opencodereasoning` | `u007.part0001.jsonl` | 270,299,793 | `2c6ea142df98144432968415e9b66356751054cb6e921650eabcf249495d25c5` |
| `sft-code-opencodereasoning` | `u008.part0000.jsonl` | 300,024,950 | `91eeb167b697037532f4d7e4bacb8435ca42126dfdd62cc79958fc739af6da42` |
| `sft-code-opencodereasoning` | `u014.part0001.jsonl` | 270,447,359 | `0680729f897d74f6c7436386d443f652c35df1d4e1cd89c8f44ae9912ccadb34` |
| `sft-code-opencodereasoning` | `u017.part0000.jsonl` | 300,020,537 | `c73516e1935a8144e286df2147b36d95bdd1cdcd1353d5dd13fb2183d659a6c4` |
| `sft-code-opencodereasoning` | `u015.part0001.jsonl` | 270,422,887 | `9fa51f6a334bc0472f2c6540dc1e19f588ce5b0abb50b0927ae59cf242610393` |
| `sft-code-opencodereasoning` | `u008.part0001.jsonl` | 270,620,095 | `0ef51894e4e702c8294cefca583ab7ea3c461e98f2bdf8bed1460346339743c5` |
| `sft-code-opencodereasoning` | `u018.part0000.jsonl` | 300,054,694 | `642c34b1a1b14d0380483625ec23d4c9c7f263b21be16a61c71b040fdfd6214a` |
| `sft-code-opencodereasoning` | `u017.part0001.jsonl` | 269,660,775 | `126fe01b17b3cae371fbec7657419506b5e0a8905c8880efe5d5dd5ea008067b` |
| `sft-code-opencodereasoning` | `u016.part0000.jsonl` | 300,002,547 | `a51cfe35c13b35dec0ac4e329790425bde1c2cce3ebdceba356c8eff53c666ce` |
| `sft-code-opencodereasoning` | `u011.part0000.jsonl` | 300,003,139 | `c1a478a1789c91497ad46e03409b3dddabccc94e47e139e0fadea20626f06f18` |
| `sft-code-opencodereasoning` | `u018.part0001.jsonl` | 269,900,232 | `c4c7828ac7a8cff413f7dc288656bf885d531d2db4744ebfb33f73608c5a4ce9` |
| `sft-code-opencodereasoning` | `u019.part0000.jsonl` | 300,007,423 | `d4eb086f600152150fc2ce09f7d9f98a7d03a5b2b7687e823d737e155034b65a` |
| `sft-code-opencodereasoning` | `u016.part0001.jsonl` | 270,105,572 | `6215389c9a7aaac98061d8232b3acc085ed375162134ca5d35e4134773d0117f` |
| `sft-code-opencodereasoning` | `u005.part0000.jsonl` | 300,019,499 | `4077237ee65b14103a1d35ebb99c559a97aa3b39a49e2874d515d40893ab039d` |
| `sft-code-opencodereasoning` | `u011.part0001.jsonl` | 269,547,307 | `5799a770e5daf3118f218174256e3d50e10bf5167299ab43c707aeffd5bd607f` |
| `sft-code-opencodereasoning` | `u019.part0001.jsonl` | 269,219,457 | `576f8c5057cce1ab7414a6d3bba699a8872377ea06c6f046406b85ef66952e76` |
| `sft-code-opencodereasoning` | `u000.part0000.jsonl` | 300,017,361 | `85e95b7ef98a6b0acce9c6280a3edb44af4abc33cdfb6743eac7846b32131c59` |
| `sft-code-opencodereasoning` | `u005.part0001.jsonl` | 269,098,297 | `6e45af60c76de8bee5f5b36fe5cfb762ea7d5bb263bbd122da247970c50f4844` |
| `sft-code-opencodereasoning` | `u010.part0000.jsonl` | 300,019,937 | `7a8982886e8724de72396e440ef002dc45a81f64b603e96a1408ae11e6e7dba0` |
| `sft-code-opencodereasoning` | `u002.part0000.jsonl` | 300,022,533 | `4be88ab10aec7854e8a455586ec10b41e78ec4c7bc74aec3061b295a80945d6b` |
| `sft-code-opencodereasoning` | `u000.part0001.jsonl` | 268,957,661 | `ae683ae6dd85f83c8307b7400328948374341a3875669068ffc91490e310caf4` |
| `sft-code-opencodereasoning` | `u006.part0000.jsonl` | 300,000,194 | `cdc2ae71e9d4c0291c17dcaca9be4b649fa2a8a80e241eff7490f5dc4bb3c2fd` |
| `sft-code-opencodereasoning` | `u010.part0001.jsonl` | 269,100,297 | `0f245d744f7c9041a0c420253c986d8028488a7793d76653db12064d46e97307` |
| `sft-code-opencodereasoning` | `u002.part0001.jsonl` | 268,764,463 | `329cf3af0ec1f6f4384a3530d987f18d240a15e59d168449fa9694ed999ecd5f` |
| `sft-code-opencodereasoning` | `u012.part0000.jsonl` | 300,017,149 | `cbbe74ceabd8035c2212fa79d2162d3e3633b121faa84db3f1d1872b08b6d246` |
| `sft-code-opencodereasoning` | `u006.part0001.jsonl` | 269,317,400 | `39074fecbec0dc342b7633bd5993bd80809d1818b0534f600a212e1bafaa7d77` |
| `sft-code-opencodereasoning` | `u003.part0000.jsonl` | 300,005,875 | `dee833ed75e683d556ded3c76b69e7bf7e5a0f26af317f61ff6ad9281adee987` |
| `sft-code-opencodereasoning` | `u012.part0001.jsonl` | 268,794,072 | `f201cf0ed0476e10270efa6b06a986e0f01eebd6a558f061a1de09a2f040673b` |
| `sft-code-opencodereasoning` | `u001.part0000.jsonl` | 300,011,404 | `e3693baac107a104ac123e6c3a37b5e9ce55cbe3ddc06e0db5e614d2c165f451` |
| `sft-code-opencodereasoning` | `u013.part0000.jsonl` | 300,045,183 | `f6f19ac4fd8e7bd3e5767bbb245c995f3591c4a9c1c4080c6b918c332f53b8c5` |
| `sft-code-opencodereasoning` | `u003.part0001.jsonl` | 268,627,667 | `119b0421017d16aa1376aa4e0bb640ad32cd784d5886275656dd322288cb4507` |
| `sft-code-opencodereasoning` | `u009.part0000.jsonl` | 300,001,179 | `5a6b58f7cc7b332ec5fe3b3723e3b74926eb63929cf0da90aee610d4f9cd53a2` |
| `sft-code-opencodereasoning` | `u001.part0001.jsonl` | 267,926,553 | `53c6c59ed631febf4d16c247902c728792feb3c6132c9a3a183b78637cd2f2ed` |
| `sft-code-opencodereasoning` | `u004.part0000.jsonl` | 300,000,163 | `576c3a057260de423a683474365012d2c6dca96455b140dc37a6f99a84826f5f` |
| `sft-code-opencodereasoning` | `u013.part0001.jsonl` | 267,747,970 | `547ab86f8545d5fd7e7b01114ddac236b780c18e204f88e26202c1b72536f002` |
| `sft-code-opencodereasoning` | `u009.part0001.jsonl` | 267,851,201 | `78c60bcc7ad5c5629332a0bb6a2be7c4830aa4747171cef01718e2a3411417a9` |
| `sft-code-opencodereasoning` | `u024.part0000.jsonl` | 300,000,216 | `8fb329faa80af96f9412275bac0df13a5f4d983692acd1317b261d257381c381` |
| `sft-code-opencodereasoning` | `u004.part0001.jsonl` | 266,729,611 | `e1befd56e074ad6c8f54cda1459018571b85f6c188276f8e1ffc728791a7be50` |
| `sft-code-opencodereasoning` | `u024.part0001.jsonl` | 268,947,924 | `d25953f5f4d06c05875c5d9b4bc7e6e55d3f69e32ffc0bfa0956bdc53fa460ab` |
| `sft-code-swe-rebench-openhands` | `code-swe-rebench-openhands.jsonl` | 6,432,083,124 | `f2c910ec7ccda9fea8b26b58958a353336a3465e020f495f14d103d9d9319dda` |
| `sft-code-swe-zero-openhands` | `u051.part0000.jsonl` | 300,046,774 | `d5d85e49d50a46e94499bdb09b70af404d009dda1a8593fbb30e5bef4ac8ddc5` |
| `sft-code-swe-zero-openhands` | `u045.part0000.jsonl` | 300,150,459 | `e20dbc865f0a95f190d2685f11da97003b8a7e640d80e92ca3bda5660df7a99f` |
| `sft-code-swe-zero-openhands` | `u051.part0001.jsonl` | 300,187,625 | `ed98415246eb34b0b07116a31da90ceb6f8c5d86db173e0376c8d1ffb13d0732` |
| `sft-code-swe-zero-openhands` | `u045.part0001.jsonl` | 300,064,551 | `bbab6721312cc6a418018adec516b837f8cf25028c336052595d14a3dae1a59c` |
| `sft-code-swe-zero-openhands` | `u051.part0002.jsonl` | 69,558,826 | `82344cd4a39bb4fdcedeb7a61ba7bf2a7ab26627d83bcacb3ee3555b77cb225e` |
| `sft-code-swe-zero-openhands` | `u045.part0002.jsonl` | 33,953,867 | `86b2e59de5d2bf86484155cf84337d907a95a0af3b465c53f0aa8612a684ca3f` |
| `sft-code-swe-zero-openhands` | `u048.part0000.jsonl` | 300,102,355 | `2534532e52507f5aa7a65acaf950edd6aa4064064dd5fe5bc236497b1d1066cc` |
| `sft-code-swe-zero-openhands` | `u050.part0000.jsonl` | 300,031,838 | `8d93bd9845d160bea21655cbe94c9ecfd6eda52f0d86b71f1764f83673f6b55b` |
| `sft-code-swe-zero-openhands` | `u047.part0000.jsonl` | 300,062,026 | `b55f7d45b72a878e05471c176f4d2591a480d40f521365a1fd62595775c0f66a` |
| `sft-code-swe-zero-openhands` | `u048.part0001.jsonl` | 300,093,022 | `9112369a8a00036b4ccdee43a81e492ce407fb650862a2db2408478566755e69` |
| `sft-code-swe-zero-openhands` | `u052.part0000.jsonl` | 300,070,599 | `6fa64495246412f5a5677564b83f3b10f190c866fa846b71c54da5b2f711dc91` |
| `sft-code-swe-zero-openhands` | `u048.part0002.jsonl` | 42,519,796 | `d954c774c450913e28a0acc4fcd4df5950be13f5cacd1017e0f1bc16a9ae5278` |
| `sft-code-swe-zero-openhands` | `u050.part0001.jsonl` | 300,028,446 | `8277a9777c70447473191b901659bd26ac5c2b9704babdbade4f34f3eb5e8160` |
| `sft-code-swe-zero-openhands` | `u047.part0001.jsonl` | 300,012,148 | `8f936712e160047d28bba82e65e138a68dd81863ccfbaa5274b2ebd522457669` |
| `sft-code-swe-zero-openhands` | `u050.part0002.jsonl` | 51,266,730 | `8834385b15efe898fa639aa17be7549f8efc24c465789e9dfa2fb3482ebc0f6e` |
| `sft-code-swe-zero-openhands` | `u047.part0002.jsonl` | 44,542,409 | `2ef9cd732aef67d1643124f49766b4151b4ea0d774b3ee05330027327695eaa2` |
| `sft-code-swe-zero-openhands` | `u046.part0000.jsonl` | 300,036,714 | `14ddf398b883e7464ec36990750fb282633d609b8ff5c53e5fe1f3534932b4b7` |
| `sft-code-swe-zero-openhands` | `u049.part0000.jsonl` | 300,098,211 | `56c99f562de0ce23d390ea022896d3b37cf9750db660658b1458902aaaf692b5` |
| `sft-code-swe-zero-openhands` | `u052.part0001.jsonl` | 300,060,199 | `de9d10da6602b5d982a6516813b5e88ec598429c7eae1d8ccd93fc925ce043a5` |
| `sft-code-swe-zero-openhands` | `u052.part0002.jsonl` | 85,293,272 | `f747c12f03f01590baf570dc4263b9405f1892d377fe29e1f520e5411b0f98c7` |
| `sft-code-swe-zero-openhands` | `u046.part0001.jsonl` | 300,045,659 | `625e9589fcecc422527256399f8b66d81ffd7cbb3109b01c1acde4e66071af65` |
| `sft-code-swe-zero-openhands` | `u049.part0001.jsonl` | 300,065,991 | `28565ca48f1882d9da5a9be58c580700acf7bddbb17be4b162cb6787064b4401` |
| `sft-code-swe-zero-openhands` | `u046.part0002.jsonl` | 39,013,935 | `5dfe5d0aa8a3a6e9805d772e97794eac7e60717a9f18a92554f4acdaf25cd741` |
| `sft-code-swe-zero-openhands` | `u049.part0002.jsonl` | 39,225,032 | `b9cbb5ec2f28cf75e01f6b981b28fb0031e673fe39ad40eb1b835d756a155c4a` |
| `sft-code-swe-zero-openhands` | `u044.part0000.jsonl` | 300,070,849 | `88c52568118aa89c90927964ae3824f42d8e4b047cfc2391ddb44246c71b393c` |
| `sft-code-swe-zero-openhands` | `u042.part0000.jsonl` | 300,083,291 | `ecf5b3b97abfd4143b06c574b32091dd07ab7cc0bea577ec68652509e67bcb4e` |
| `sft-code-swe-zero-openhands` | `u044.part0001.jsonl` | 300,030,212 | `0940ffab0590553bbd37880c39aee920e32df03d4ad0e04592fb8f7253bbaa02` |
| `sft-code-swe-zero-openhands` | `u044.part0002.jsonl` | 33,356,579 | `6165d89469c9c5130fb30b4822ac6f0fea93749dd2f172ec684dd5a50e2ec8f4` |
| `sft-code-swe-zero-openhands` | `u042.part0001.jsonl` | 286,098,097 | `0fc9d5d014bca0a15950d75000ac0f3afed8d7eaacc5bfab49742e7818c0bc6c` |
| `sft-code-swe-zero-openhands` | `u043.part0000.jsonl` | 300,047,467 | `67e798c632faaddfa2b7d0296c7ec2a93acc08bae5534a38e44df5bcb75d0a99` |
| `sft-code-swe-zero-openhands` | `u038.part0000.jsonl` | 300,008,731 | `7ae974e1ce31de65201f6842af357b9d9fef52264712bb15f41b31c575f39260` |
| `sft-code-swe-zero-openhands` | `u043.part0001.jsonl` | 289,582,629 | `30a2ac1b8744f753007f86f179ce648ad73cce8902dd00dbc504120a64229770` |
| `sft-code-swe-zero-openhands` | `u038.part0001.jsonl` | 259,797,047 | `643257f749e2122b7c6b8a67bf898e1b0fdec3ddac6e9b2e110b4ec58ce41a08` |
| `sft-code-swe-zero-openhands` | `u040.part0000.jsonl` | 300,076,641 | `ec0818dfd860a2849a411af0f0932d7747be929605ff4912862c0079fa55617b` |
| `sft-code-swe-zero-openhands` | `u062.part0000.jsonl` | 300,046,264 | `63124fbb0cabda12b51f5672afcaa386e8a57a674c049aa49a9fdf6c03856f7a` |
| `sft-code-swe-zero-openhands` | `u040.part0001.jsonl` | 282,642,225 | `a666ed04e6c39d8fe5c9ef8c2c7a1616063e0fc7e4ddfdcdba326616c392b2e2` |
| `sft-code-swe-zero-openhands` | `u062.part0001.jsonl` | 279,906,783 | `c04483a3b1751de61279bc61fc7ccf7c075f6ecdedbf9327d13396ab8987e9bd` |
| `sft-code-swe-zero-openhands` | `u041.part0000.jsonl` | 300,026,269 | `254bf1c0eb8466b83cceaff4a765642e2b0a672063f514ba67b9faafb1d2e09a` |
| `sft-code-swe-zero-openhands` | `u041.part0001.jsonl` | 281,984,411 | `514938e4258daa683111188ddd405dc03697495a04d606d5337ca7302068e735` |
| `sft-code-swe-zero-openhands` | `u034.part0000.jsonl` | 300,009,326 | `a4288f4df16b9675266d277b578698aa88a2f5d618c9d4286c93d74f97172115` |
| `sft-code-swe-zero-openhands` | `u034.part0001.jsonl` | 260,627,151 | `60e3ef0159541fc834e33254dce581864b0408b581939303f7793ef586a36757` |
| `sft-code-swe-zero-openhands` | `u036.part0000.jsonl` | 300,133,482 | `8663c9b2ea0bbb3a9ac855d7422f2bd6c3be5e3301880a87d7690e35176dd0f0` |
| `sft-code-swe-zero-openhands` | `u036.part0001.jsonl` | 262,812,942 | `082641367ebf53fb7a5a67b4775a2007c3d024f9518719b21401e8252b632d35` |
| `sft-code-swe-zero-openhands` | `u039.part0000.jsonl` | 300,032,802 | `25240467a96e107ee6d3cc7645a83f685a63665a1c124f24ad7275dde3f1e4c2` |
| `sft-code-swe-zero-openhands` | `u039.part0001.jsonl` | 260,517,829 | `7162b055f8bfdfd3d84faf308d4d655aeaa9de2b9d6f84cebaef7c0121675518` |
| `sft-code-swe-zero-openhands` | `u035.part0000.jsonl` | 300,125,560 | `ca13a54578618afe79f63541e45cfa3e682162a5e3d9afc5d3165fb9c767628d` |
| `sft-code-swe-zero-openhands` | `u035.part0001.jsonl` | 257,066,891 | `16181310dbee33773a12ea8fc6cde0d78d1ffff7e604156b8d26baaaa8787ba2` |
| `sft-code-swe-zero-openhands` | `u037.part0000.jsonl` | 300,077,761 | `70eacc86e9ab7c20506194c19e78e36353c33ae3921f2f4972ae21c6a6a63218` |
| `sft-code-swe-zero-openhands` | `u037.part0001.jsonl` | 257,730,683 | `deb648799c828950abb14f39467133c964a6efc60f382bf6d1c07ef6c6aa893c` |
| `sft-code-swe-zero-openhands` | `u009.part0000.jsonl` | 300,066,146 | `1c7d46a85b55d2b0c09f8ac9a29c38a35a44f750e48b0bec7b699f7dc629aaa1` |
| `sft-code-swe-zero-openhands` | `u009.part0001.jsonl` | 224,294,229 | `266d3737ed67c97c38ee0a828e50812d0a47d3a5b82c8262f577f18b8e8f16a0` |
| `sft-code-swe-zero-openhands` | `u061.part0000.jsonl` | 300,048,324 | `eebd20dcd1efe9529884722ac45c4b4b42ed84508c331b00f97721536e2c27bb` |
| `sft-code-swe-zero-openhands` | `u061.part0001.jsonl` | 253,774,686 | `0fb34e3a35665e74fa3499e624159dde58c69df5b32c1f24749dc63c6455de02` |
| `sft-code-swe-zero-openhands` | `u030.part0000.jsonl` | 300,029,063 | `65c2ffcfb61d3471afae3e25ce4fb35944323bee1893e087ac4a898465e9fa48` |
| `sft-code-swe-zero-openhands` | `u030.part0001.jsonl` | 222,774,007 | `91fcb9775f517e9e752de92469ec3efefb99bf8e5912c299c686722f33968038` |
| `sft-code-swe-zero-openhands` | `u056.part0000.jsonl` | 300,019,982 | `7dc31d9f326b6cefd630de74443dc3918916f273947a9ebc28e4b20f1fd65451` |
| `sft-code-swe-zero-openhands` | `u053.part0000.jsonl` | 300,028,076 | `fd0b633feb056010bbc47aee9b5590513208b6b170ca504ed70861e6c8830308` |
| `sft-code-swe-zero-openhands` | `u056.part0001.jsonl` | 223,328,777 | `7de8cb796405730419462e5be9c17f759bd643e728f7fa154176907f143b0d73` |
| `sft-code-swe-zero-openhands` | `u053.part0001.jsonl` | 240,281,446 | `381051e4f76e5a48ceca2efcf4a5f2adf40ef7ac6c4d6e8b4e3b2827c0d7e207` |
| `sft-code-swe-zero-openhands` | `u033.part0000.jsonl` | 300,048,958 | `a5360c788125ad35535138b3c99fac127777b710bc541404b7725dcde5369c8b` |
| `sft-code-swe-zero-openhands` | `u004.part0000.jsonl` | 300,088,855 | `c1de12e994023c65f6341508ad946834b323e0fed19174d526d6e6ddc1aa3cc2` |
| `sft-code-swe-zero-openhands` | `u033.part0001.jsonl` | 234,847,100 | `6f91c1bcb0edaa0a98e3ab29a7c3d174e8d2533ff4da853f503e433984e53369` |
| `sft-code-swe-zero-openhands` | `u004.part0001.jsonl` | 221,696,750 | `2402317045e1550e9d849a934703e028b07a772933e8dbd4cc21266c5ffbabe7` |
| `sft-code-swe-zero-openhands` | `u020.part0000.jsonl` | 300,164,785 | `75f676ec9a86c9d30af58bde0a41b4681397fb246f4c9f713e3c7340bf2451ab` |
| `sft-code-swe-zero-openhands` | `u020.part0001.jsonl` | 222,679,158 | `6e281f93c49dcc77f4ec069756e89de380c2f9898e372ca4364e8ce78d8e74ec` |
| `sft-code-swe-zero-openhands` | `u021.part0000.jsonl` | 300,017,275 | `8aa78719cbcfba78f1de18151e11ac928e725ec01faad711099a4d33b774e05d` |
| `sft-code-swe-zero-openhands` | `u021.part0001.jsonl` | 229,820,829 | `aa58e78b3b7facb2e2d8efb0aeb4f7b19403d4de77562b532876a6d94a2fc3ad` |
| `sft-code-swe-zero-openhands` | `u010.part0000.jsonl` | 300,069,688 | `575408f4fc5cfcb6443735d75cebf8f2e559e8a7df8b8e6d92e7d71587c3468b` |
| `sft-code-swe-zero-openhands` | `u010.part0001.jsonl` | 231,565,016 | `590e64d00efb6aa53a91ae8067ca14be03a1ef044f050c57b7af2fa930032de5` |
| `sft-code-swe-zero-openhands` | `u027.part0000.jsonl` | 300,057,116 | `04d05981b6081febc6b42742687d42f8360ae4fae4bc88136823b44627f701d2` |
| `sft-code-swe-zero-openhands` | `u027.part0001.jsonl` | 227,834,940 | `7feb155ade02d8138b76fffc762adea850101b232c10e14513700e0ebea0a80a` |
| `sft-code-swe-zero-openhands` | `u026.part0000.jsonl` | 300,006,474 | `8d429869ef771fdb0b959054146fe9b5c7f4c53aecc5f0ed6ff1b7225859cee5` |
| `sft-code-swe-zero-openhands` | `u026.part0001.jsonl` | 228,609,540 | `c81947dbe93e47ece4df581d6d84fd7276d2cf1b9c578a2cea49b8a70e2b1167` |
| `sft-code-swe-zero-openhands` | `u029.part0000.jsonl` | 300,076,665 | `8b41ba5951de48004b3e843d0db794dc41a04e9595cfff269df530a54852b57f` |
| `sft-code-swe-zero-openhands` | `u029.part0001.jsonl` | 226,863,475 | `e7bb715f77c9274203b643c61722ac8e4747a691f6ea8ad00589cb77b882dc0f` |
| `sft-code-swe-zero-openhands` | `u013.part0000.jsonl` | 300,105,476 | `23da618bf439cea613c972090752552ca9c89da167bbabc1273c8126b90ee96a` |
| `sft-code-swe-zero-openhands` | `u013.part0001.jsonl` | 220,410,838 | `d2454a9f88bca430dc5a770951004fc4386d27bf53e52ed70bf6a74e602638dc` |
| `sft-code-swe-zero-openhands` | `u008.part0000.jsonl` | 300,073,998 | `087ae8784842e2347266a804645515c8832e9ca3f21632080d96ad099f02ab1b` |
| `sft-code-swe-zero-openhands` | `u008.part0001.jsonl` | 224,869,646 | `2fe31909c33b175b9c48f3dd00a6c128ebaa097dafa4449a6318825e3dbdcc6d` |
| `sft-code-swe-zero-openhands` | `u005.part0000.jsonl` | 300,013,363 | `8c1fe3ea5ff024c0effeeea06ddee9f2ab74237fb33ab38131ad09697711ca0c` |
| `sft-code-swe-zero-openhands` | `u005.part0001.jsonl` | 220,751,569 | `2020515e0d62a60edc7dd07e63536750e767096b96812d477a29a72d50d7aa57` |
| `sft-code-swe-zero-openhands` | `u031.part0000.jsonl` | 300,011,295 | `f91c4a301a1fa951277adffdb90b2fb17de6505fe04a5aeae8fff42a9440c54f` |
| `sft-code-swe-zero-openhands` | `u031.part0001.jsonl` | 226,669,051 | `4a35f89b93ac92b6a9490c89b52d5f05b29324ac1a13f8fb4c27884a78a03c2a` |
| `sft-code-swe-zero-openhands` | `u022.part0000.jsonl` | 300,054,557 | `ad8090a8637dce201308282c38cea49d9cdbf335e58067e1583ff10cce7ef49e` |
| `sft-code-swe-zero-openhands` | `u022.part0001.jsonl` | 227,524,515 | `7b6d5a13266e272a28a6be9cdaf9360679b71075c31d3dc29a4c52c2c369e9b9` |
| `sft-code-swe-zero-openhands` | `u015.part0000.jsonl` | 300,008,517 | `c433a5a65a40f4f5a7e90e4afe446dbadb8da110a212f92073e65eb4c0ad16b9` |
| `sft-code-swe-zero-openhands` | `u015.part0001.jsonl` | 224,836,399 | `44ac19aa9d81e2ea19f9663a105e978b6b14f65b22614ce6ba63bf1213b4b941` |
| `sft-code-swe-zero-openhands` | `u018.part0000.jsonl` | 300,059,288 | `0ea96826256446fc3be9b85ea175ea10fbc22bcab59ff0eeb637c19edb33eeec` |
| `sft-code-swe-zero-openhands` | `u018.part0001.jsonl` | 227,070,136 | `c53e59610664f7f56fb86419d29e21143ebcc89f28ec0a1474ae691e3a57d439` |
| `sft-code-swe-zero-openhands` | `u006.part0000.jsonl` | 300,010,750 | `a5956a34790302b58b2c9bfb933a2e57f27d32f4e4f79b37e13388035c41d852` |
| `sft-code-swe-zero-openhands` | `u006.part0001.jsonl` | 222,434,990 | `25b5881ee92b91510ae1422247a1991dcf8915ba6c1a390b6e624248a16b88b0` |
| `sft-code-swe-zero-openhands` | `u023.part0000.jsonl` | 300,068,149 | `17b3042c40b1d3276d1272f7fcac9035f6332335921b641c7385b8318c22c0a0` |
| `sft-code-swe-zero-openhands` | `u023.part0001.jsonl` | 225,977,033 | `227893d4cddc91a5c8d21584061769bbafdbf87f181e2d93fd02a3e8c1efe629` |
| `sft-code-swe-zero-openhands` | `u011.part0000.jsonl` | 300,071,835 | `a957645304fe115b2adbb149a3432d63a08be08a0510ec0441912f94f81a2017` |
| `sft-code-swe-zero-openhands` | `u012.part0000.jsonl` | 300,073,583 | `5798d80f7ff0bda017e5ac8828f72fd35b1c4e1d578789456e18a5f937707f5e` |
| `sft-code-swe-zero-openhands` | `u011.part0001.jsonl` | 225,868,505 | `6295fb3c9dbf092ccd477e7759c7816cc5c8c93f7c3b45c3b661bd801345daec` |
| `sft-code-swe-zero-openhands` | `u012.part0001.jsonl` | 226,245,624 | `170220ec08eb364aab8328fa3fc76a2afd66e1b9a6c34977c91205ef4725625f` |
| `sft-code-swe-zero-openhands` | `u007.part0000.jsonl` | 300,063,282 | `434b8adba99d021fc8753c0d5af43557145362056bb0d864e06cffc66979df9a` |
| `sft-code-swe-zero-openhands` | `u007.part0001.jsonl` | 223,863,771 | `baafb983f403126508fdb75f29aa1f151b44a9d49cc251f85486f1e4a8660ad5` |
| `sft-code-swe-zero-openhands` | `u060.part0000.jsonl` | 300,018,335 | `4d1d4d6c4d22020dcb761da1c4d74b84d7f85e2dd5dcb6c2309b21c8cbf962f2` |
| `sft-code-swe-zero-openhands` | `u060.part0001.jsonl` | 230,560,447 | `19521a0d4eff06981da97c348c7d64838da8639dd9dcc8718fe23ea727e5e10a` |
| `sft-code-swe-zero-openhands` | `u016.part0000.jsonl` | 300,046,918 | `5e01f5825e377497c78e8e760a18a2a24224f71e4ab7aef8b8c16bec37e67387` |
| `sft-code-swe-zero-openhands` | `u016.part0001.jsonl` | 226,273,462 | `247a21c7427d8ace87f9e60a2638a9e02731e1674b1d2c7dc67f6d19feb85411` |
| `sft-code-swe-zero-openhands` | `u032.part0000.jsonl` | 300,023,069 | `53ba9272beb4b141179d2870cf8004fcd1e0f293039708fd2a46339db6f88f58` |
| `sft-code-swe-zero-openhands` | `u032.part0001.jsonl` | 225,776,990 | `435b49328e2ba8ef27f1fe910124a00359c62e1ea9daa4d9c6fb21d8fdb3ef0c` |
| `sft-code-swe-zero-openhands` | `u014.part0000.jsonl` | 300,078,435 | `b65c69d707a8f0e614bf093062157be8b4887ef1d1cf44ed5a086d178ecd53ca` |
| `sft-code-swe-zero-openhands` | `u014.part0001.jsonl` | 221,784,267 | `58a755240f84613a254a81f50715003fb4cbd0bbef3254dddbdc9e1763356cbe` |
| `sft-code-swe-zero-openhands` | `u017.part0000.jsonl` | 300,019,222 | `506a37dcb0820801a65e4e52e4cd7ba08b4ab9a192ca3549e48a37290537a1b5` |
| `sft-code-swe-zero-openhands` | `u017.part0001.jsonl` | 226,423,996 | `bb9d508596444b69e597a9110b2f12cd82ba3cd550e3ce2637cc10f3d0c7d441` |
| `sft-code-swe-zero-openhands` | `u028.part0000.jsonl` | 300,002,525 | `1a8149030c344a7648d0f9b607a665a8769487b28d000088d176844864a13b47` |
| `sft-code-swe-zero-openhands` | `u025.part0000.jsonl` | 300,001,902 | `84123057af48ece34465ee6489bc50806cb18aae53eca4b33e3d319895821c24` |
| `sft-code-swe-zero-openhands` | `u028.part0001.jsonl` | 225,163,584 | `5ba710504dcc409269f04394692fcd1ec39be1c9ec006fa2e1be6806807ad9c6` |
| `sft-code-swe-zero-openhands` | `u025.part0001.jsonl` | 222,277,854 | `e81194a92452e73c1a8a00c8975f8a75fdd40d8bbddc0ef36e4b0e41276e903a` |
| `sft-code-swe-zero-openhands` | `u019.part0000.jsonl` | 300,005,022 | `0f7c4da158f03a8c6b23df55204c9c0220800bd1ad796f2d0bb2eeb234da375c` |
| `sft-code-swe-zero-openhands` | `u019.part0001.jsonl` | 226,791,728 | `ea92874bf2069340e95ae8450fd10df3568a80d7ca03f3b0b482105bfc8d9f51` |
| `sft-code-swe-zero-openhands` | `u000.part0000.jsonl` | 300,018,833 | `d78945f5261ee6eeea19e67fb989762ab33fe41afa64409a87bf2cb104fbc041` |
| `sft-code-swe-zero-openhands` | `u000.part0001.jsonl` | 227,698,379 | `4e2f1a939334d8b4c77572ec74778100fa75fe3f7566113a712017b94c7ccc18` |
| `sft-code-swe-zero-openhands` | `u003.part0000.jsonl` | 300,100,975 | `fdacebb6ad09dc168c591fcd0143abb685bc5c7d1aa1079c59b4f15cface472b` |
| `sft-code-swe-zero-openhands` | `u003.part0001.jsonl` | 221,549,781 | `e8774c961a4813351a86be80792a5a6b378addd3cb8ec0026bc4b1c52b317a79` |
| `sft-code-swe-zero-openhands` | `u024.part0000.jsonl` | 300,018,247 | `0e9501726e9ee381807767c1696bd2d3a6aa1d8da3ff33ccc105d11dbd47dbde` |
| `sft-code-swe-zero-openhands` | `u024.part0001.jsonl` | 220,519,172 | `e1f0ef4926d43857247aa7a2f1de42a624424ddba03b821bf6bf2a9df34b2236` |
| `sft-code-swe-zero-openhands` | `u057.part0000.jsonl` | 300,044,451 | `dac6fb4f3f0391f653265b748fddc4db78b1845aab771775a4db0085143f3233` |
| `sft-code-swe-zero-openhands` | `u057.part0001.jsonl` | 222,114,052 | `25921cfa4c1eaab4c67d1aab41e8dbb547887f6c37a7b836963d2a698595e7f9` |
| `sft-code-swe-zero-openhands` | `u001.part0000.jsonl` | 300,024,578 | `3e7ca3ffa1961a85f0436d21935e87f1ce5a63a1f93e231c87722e53e26648f8` |
| `sft-code-swe-zero-openhands` | `u001.part0001.jsonl` | 221,003,182 | `c31884117bbc2e5c267a77d1bf47297e647eca62bd916ddba02fdd41cf49cb90` |
| `sft-code-swe-zero-openhands` | `u055.part0000.jsonl` | 300,083,566 | `3ea0df95edc8911c280c213b44d6828b1a32b3d0a691ab4305c744fabfe5220f` |
| `sft-code-swe-zero-openhands` | `u055.part0001.jsonl` | 218,822,572 | `d076f9c6701e728d8db3482ad42970ca0be45b96be859f28ad3e6403ec8417cb` |
| `sft-code-swe-zero-openhands` | `u058.part0000.jsonl` | 300,148,751 | `eb3b49ba29e0d582c031a253ff27d17e0f497b5fd64896fbaa77f35642a427ae` |
| `sft-code-swe-zero-openhands` | `u058.part0001.jsonl` | 217,820,697 | `5ade8f6e168b66d8fb8fa6f3832f00c18cd5b0dd4ee5350c6d954b86a7d3d1c3` |
| `sft-code-swe-zero-openhands` | `u059.part0000.jsonl` | 300,111,704 | `e86cb016205fce6d795e1743e973edf146ddffc82c136b2777af0ca635da5a7a` |
| `sft-code-swe-zero-openhands` | `u002.part0000.jsonl` | 300,121,822 | `48d76908ec5618844746cea891a472ce6bfab938bae49ca68179dc8bc33d56ac` |
| `sft-code-swe-zero-openhands` | `u059.part0001.jsonl` | 216,980,839 | `87b4e264cf828fbfecd399653eadaaa00390227dd54d30280dddd3ad135567f2` |
| `sft-code-swe-zero-openhands` | `u002.part0001.jsonl` | 222,031,374 | `c0c68bf884c657c40011af29d4676f0692612977651c27a629a44dee92158f9b` |
| `sft-code-swe-zero-openhands` | `u054.part0000.jsonl` | 300,004,593 | `3dc068f199e67c64a7fe918500635f6acd7d2b7b42084b030d86ba430c495ed7` |
| `sft-code-swe-zero-openhands` | `u054.part0001.jsonl` | 188,035,216 | `f0983439254caa512b0d286ae1c40b80e8eb0667a6429cb617a372ffecd4c084` |
| `sft-code-swe-zero-openhands` | `u063.part0000.jsonl` | 300,051,959 | `5a99bbdddd88defd6cf65ce0ac1057c51d462e23262b3fc6c723ee9605b28295` |
| `sft-code-swe-zero-openhands` | `u063.part0001.jsonl` | 76,003,515 | `b689aa93304adec95025061c3ac80b14d86477826f40129e489d31428165222f` |
| `sft-dolly-15k` | `dolly-15k.jsonl` | 15,465,770 | `f0e65f12ff0437552f9d8340c5244758ca233693c7c4c982480f3fcbfb50714a` |
| `sft-indic-aya-collection` | `indic-aya-collection.jsonl` | 2,668,534,387 | `be59e274c47778c906e0f5fa531ca5c8c195f29189ef8d09dd046d6beabae9eb` |
| `sft-indic-aya-dataset` | `indic-aya-dataset.jsonl` | 106,423,427 | `fbaf54e2913face83c7a9d1a25b87e086ce574b5debb840d2d159681b0bcb2ea` |
| `sft-indic-indic-align-dolly-t` | `u000.part0000.jsonl` | 16,609,790 | `3af21a7c294ccaa362cda5b22af00b538879f5683dc5745a7aedc26efe437786` |
| `sft-indic-indic-align-oasst-t` | `u000.part0000.jsonl` | 88,323,173 | `d672b433316d3fba14398ded7bf6c4583002669ec0cf15b8262165b6d0ef3480` |
| `sft-math-nemotron-math-v2` | `u004.part0000.jsonl` | 300,011,632 | `dc76b50a648933be117aeb4697f3049202e9a7cfea42003827ebd09eaa4f12eb` |
| `sft-math-nemotron-math-v2` | `u003.part0000.jsonl` | 300,005,514 | `22a46eeb89a2a8d72191790cfbd20c17b463bf4291e8c9f4a0cec1e3b31acd1f` |
| `sft-math-nemotron-math-v2` | `u002.part0000.jsonl` | 300,026,748 | `cd929f5022ada43ec9d8b2a22a46b75b11b810df4486aff361030f6a7e47a229` |
| `sft-math-nemotron-math-v2` | `u001.part0000.jsonl` | 300,007,784 | `c283090bcc9da37f871d00abbd26a14e2076e0b817e28805539e492e0a418ac8` |
| `sft-math-nemotron-math-v2` | `u000.part0000.jsonl` | 300,037,768 | `ebac11cbcbe6d89b871c633bceabaf5ac72f64686aa093b4c35e64de21b5a4ce` |
| `sft-math-nemotron-math-v2` | `u004.part0001.jsonl` | 300,008,041 | `914bb642172af462bf7afaf1d4f01eeec0fcc03aeb6c03d1d78235ebeb845dbe` |
| `sft-math-nemotron-math-v2` | `u002.part0001.jsonl` | 300,117,121 | `b70121e96ffa6c422cc82b51ec71db54d93d810d163e301fff08712ccac6048e` |
| `sft-math-nemotron-math-v2` | `u001.part0001.jsonl` | 300,020,207 | `2ab1100e4fcd41f4df4a64a0ac3f15db1718a4b28472e4b153a37b5662f1ce79` |
| `sft-math-nemotron-math-v2` | `u003.part0001.jsonl` | 300,001,575 | `04021a7241786e902b8990028e0437d21be85b0185f729178ba2da09a28d2c52` |
| `sft-math-nemotron-math-v2` | `u000.part0001.jsonl` | 300,085,349 | `552bd093abc2ff9f4e575f1c871a5f12ba049ec3c505ecc847c5a3f3b516d057` |
| `sft-math-nemotron-math-v2` | `u004.part0002.jsonl` | 300,000,080 | `a6214f67e51340214d5dafbcb325b67c90f9993ea5967c5e68d92328583df730` |
| `sft-math-nemotron-math-v2` | `u000.part0002.jsonl` | 300,009,147 | `c8a509051754d1ef9e3793268a55a419d743ba0859de063bbf53abea5175a3df` |
| `sft-math-nemotron-math-v2` | `u002.part0002.jsonl` | 300,048,183 | `92403ad1da088981ea534904fadbabfae7eff9901cfce836a23a6bb04f67f561` |
| `sft-math-nemotron-math-v2` | `u001.part0002.jsonl` | 300,011,951 | `e6decda4ffe3514d7a13655146a5cbdd495ba98bf4b962a4e4432b33c3215376` |
| `sft-math-nemotron-math-v2` | `u003.part0002.jsonl` | 300,002,517 | `04a22fc18181b9778f794288d4f8e151084530acc7634c050429870146ce0392` |
| `sft-math-nemotron-math-v2` | `u004.part0003.jsonl` | 300,029,669 | `44b1e09881ae904d98233bac1918a668322055bc603a725394443b78d816f96f` |
| `sft-math-nemotron-math-v2` | `u000.part0003.jsonl` | 300,003,989 | `2d36e011fb462cb75ca3df309de96159fc46b7201fe718af619512aa147005ba` |
| `sft-math-nemotron-math-v2` | `u002.part0003.jsonl` | 300,002,468 | `6db7f77c727d89e3f99f1306409d9f55f048174ca80c66c2343b78473de55978` |
| `sft-math-nemotron-math-v2` | `u001.part0003.jsonl` | 300,067,862 | `41626f993fd5893b5a86f4883b4c9f60d2e6b4a96b11b2e3e048957dc98107c6` |
| `sft-math-nemotron-math-v2` | `u003.part0003.jsonl` | 300,002,082 | `3abaa486a3d1e2dd00a86b24a6eaf3972db3a2b950853d5fde6878cd25194205` |
| `sft-math-nemotron-math-v2` | `u004.part0004.jsonl` | 300,009,138 | `b375edba09acf13cea0e6eb7af821c2ec313089c08436d1038fa5b91fe254a78` |
| `sft-math-nemotron-math-v2` | `u000.part0004.jsonl` | 300,105,552 | `919733725abe1acb8a0249464fd9b56121a89e613f41a63351d8a33c20b5d480` |
| `sft-math-nemotron-math-v2` | `u002.part0004.jsonl` | 300,013,738 | `5270c306eee2544957341aa711bac2a9944be0a9e328b21f8fc9978128b312c1` |
| `sft-math-nemotron-math-v2` | `u001.part0004.jsonl` | 300,083,249 | `c52c67bf4015d5f00eeca23af6369eef6254824ab38e0397d6eaab7fdbfdfa11` |
| `sft-math-nemotron-math-v2` | `u004.part0005.jsonl` | 300,010,292 | `1a72a60862a93173eb410f7efc0ee54870efd2a50d99ab790d9c2ae2479280f8` |
| `sft-math-nemotron-math-v2` | `u003.part0004.jsonl` | 300,003,644 | `2e99974cf97123d136e735fe966c0ccd1bc01a2ae40416c82a288d88b7ac6767` |
| `sft-math-nemotron-math-v2` | `u002.part0005.jsonl` | 300,008,636 | `7763183801e20462dc97804b9a3de787de6d7888fb4bab5f4bf503e2243113b7` |
| `sft-math-nemotron-math-v2` | `u001.part0005.jsonl` | 300,038,629 | `3a9fc1db02184fe0d63290005e3b2f3bc6341c60ac84d3519384f2808c2f904b` |
| `sft-math-nemotron-math-v2` | `u000.part0005.jsonl` | 300,101,200 | `1a791db3547248139fb96c710d525e495548b39dbf3f5600cb2650f2c2ed0a90` |
| `sft-math-nemotron-math-v2` | `u004.part0006.jsonl` | 300,003,386 | `beccea7e23abaf5c88fbe9000b7dd174c8081781d9595710fa3508c620b6fcbd` |
| `sft-math-nemotron-math-v2` | `u002.part0006.jsonl` | 300,036,570 | `7e59c7eb4b4d63fce676294aa7f69386c1885118a393f3f9c25062af47562183` |
| `sft-math-nemotron-math-v2` | `u000.part0006.jsonl` | 300,079,112 | `de76599b6d323ac760315b30ee79bf12d7dd0dcd48dbcd63ea2568120507d3a5` |
| `sft-math-nemotron-math-v2` | `u001.part0006.jsonl` | 300,038,121 | `57597219f8d36911a05c0a55fcb2c909a105f90f531a76fb305c2da36b117e69` |
| `sft-math-nemotron-math-v2` | `u003.part0005.jsonl` | 300,003,842 | `d8e74870dd7a3f023828c4527177f39dd15b92b94f8d28980827dc3ffcb4913f` |
| `sft-math-nemotron-math-v2` | `u004.part0007.jsonl` | 300,007,170 | `a089ce0c374a4bf68feffdc46177b49380ff9a3cb710e5c4159e939ea5f6c361` |
| `sft-math-nemotron-math-v2` | `u002.part0007.jsonl` | 300,130,498 | `60eb071288778b784ae705364eea8f8bad2ec4ffa89e3191aaeb76d57de9e0c2` |
| `sft-math-nemotron-math-v2` | `u001.part0007.jsonl` | 300,084,675 | `b657803f9c8d537b7d556a34599bbe68c008bbf014f1afc41d2693c8e4d70ad2` |
| `sft-math-nemotron-math-v2` | `u000.part0007.jsonl` | 300,046,424 | `5974212c0e7dc7ae3fe0eb0555a3de954b7478fbe8768df63c6a0f90a5be8436` |
| `sft-math-nemotron-math-v2` | `u004.part0008.jsonl` | 300,022,684 | `1a2b6e3c8f2ccc475c333e595e367e9e2e6074f0b244a8664156751bd5e33f44` |
| `sft-math-nemotron-math-v2` | `u003.part0006.jsonl` | 300,001,816 | `49f95b1a1c488833abc3ff21ee5e834308566cddb6d6a028f5e137069cc402b4` |
| `sft-math-nemotron-math-v2` | `u002.part0008.jsonl` | 300,026,294 | `862eb6016d1ef6cd906fa9916555dd11d143a025b618158756bee00078351683` |
| `sft-math-nemotron-math-v2` | `u000.part0008.jsonl` | 300,072,766 | `dc96d0ee7d87e82a249a5ad80f12a319a0d406a6a324fb3937fb6bf9c5ce30f9` |
| `sft-math-nemotron-math-v2` | `u001.part0008.jsonl` | 300,015,478 | `315ce6e97eb845182aedfab1d6f7a948cfbdb0b4d772a1334d0c4f82aa0e9687` |
| `sft-math-nemotron-math-v2` | `u004.part0009.jsonl` | 300,002,905 | `0a4259b04cfc2a8552412870f7ffe7104efe6ddf14acee5ba6f47552b8394fcf` |
| `sft-math-nemotron-math-v2` | `u002.part0009.jsonl` | 300,023,506 | `4337c0e2c5d5f09ff9f671893351aacfa5612e003cce191c43c9286727b168d8` |
| `sft-math-nemotron-math-v2` | `u000.part0009.jsonl` | 300,058,129 | `120d5a75a6c7b06ad520b8eb4bfd299e16a574edaa616196ad8ef2747da4c305` |
| `sft-math-nemotron-math-v2` | `u001.part0009.jsonl` | 300,024,283 | `b9c7688dd71d45be8dcb97f412203360f4b13656267600dc193a1359d799a1db` |
| `sft-math-nemotron-math-v2` | `u003.part0007.jsonl` | 300,004,950 | `16ce20458420ea9b5a6a2f4550885fdf920623be64a0a1b0d8c4c296dcf8d3ba` |
| `sft-math-nemotron-math-v2` | `u004.part0010.jsonl` | 300,001,538 | `b423a347cdfa8a81e8943b1a3a8ffd6f78290c1b766f5870261ddf948d3301b6` |
| `sft-math-nemotron-math-v2` | `u002.part0010.jsonl` | 300,043,545 | `ce00144d8ad3e7d0e6586eae87be2cefa46463b8b28d9071c9adf067c9d9655f` |
| `sft-math-nemotron-math-v2` | `u000.part0010.jsonl` | 300,125,611 | `7a59232b28291fb5fad4e1d8e9d698c2a26ce42f6983c58612d8b65befbf80e7` |
| `sft-math-nemotron-math-v2` | `u001.part0010.jsonl` | 300,012,153 | `52327777c8b8e4062e226680e80dd4a886074c1280cced5380bca63bbd15bd89` |
| `sft-math-nemotron-math-v2` | `u003.part0008.jsonl` | 300,003,460 | `d19b5306709e0fd2518bae9c6ccb1478f28ede6799b6de91233b7f24254d6b3e` |
| `sft-math-nemotron-math-v2` | `u004.part0011.jsonl` | 300,000,151 | `21fe2229ee766081f4457d04aee654da376cd99f81462e3d1f7ad8a1bf47cbb5` |
| `sft-math-nemotron-math-v2` | `u002.part0011.jsonl` | 300,007,582 | `1a9af05ea10965b486ecf6d3b5e6d2812c89255669d62b6c10527af42c90a7d9` |
| `sft-math-nemotron-math-v2` | `u000.part0011.jsonl` | 300,125,510 | `56ece8689e2c6603a3762fd954d66bced7b7f6d06d702585b6f8eaff97b4fa15` |
| `sft-math-nemotron-math-v2` | `u001.part0011.jsonl` | 300,026,814 | `022734d0a2f2b31b4cefe3d7ba9d53249e59b2b477c8209903f14f8243098a70` |
| `sft-math-nemotron-math-v2` | `u003.part0009.jsonl` | 300,004,548 | `36c5dbc4cbe62932cebecc5291ee3ad35ed8817085674369cfc0069de4418795` |
| `sft-math-nemotron-math-v2` | `u004.part0012.jsonl` | 300,000,159 | `7c063fbf28be706831d331e7436d0dd75fa20d2042a8db56574a76960c097702` |
| `sft-math-nemotron-math-v2` | `u002.part0012.jsonl` | 300,040,037 | `6bddd58ca866bc6e4c16bdeaaf49fea675261272bc5707bf494b405adf289c35` |
| `sft-math-nemotron-math-v2` | `u000.part0012.jsonl` | 300,019,065 | `9545183d6308a493364fd074bccbed2b62321548339d8ba724cb424b415afa2a` |
| `sft-math-nemotron-math-v2` | `u001.part0012.jsonl` | 300,037,934 | `82e8db002189db6ac8bac42166c9837030b56a248d0e01fef258e9059e1eac15` |
| `sft-math-nemotron-math-v2` | `u004.part0013.jsonl` | 300,006,147 | `b99ee9bcbf63c02543828d300cf3472417e33535afdfb7c2f3cdcd07d9ee4d04` |
| `sft-math-nemotron-math-v2` | `u003.part0010.jsonl` | 300,000,462 | `a0f661d27d29e8fb797cb0f73f13c1c6e9a098e1057f4f1fc8b635b0b2fe9262` |
| `sft-math-nemotron-math-v2` | `u002.part0013.jsonl` | 300,043,366 | `43b9ac889f1a44cd45855a908a4c3b9b51520e08e8f2f01e1f29186eab1a32b4` |
| `sft-math-nemotron-math-v2` | `u000.part0013.jsonl` | 300,005,868 | `75b6d4d2b4a241144a07bcacadfc486b319ada16a07bbfbfb8bfdb0de2d0f358` |
| `sft-math-nemotron-math-v2` | `u001.part0013.jsonl` | 300,008,664 | `ad8661560d49312fa54bac4ec5b07edd3f9863450f05ffed5d78f65ba977a09c` |
| `sft-math-nemotron-math-v2` | `u004.part0014.jsonl` | 300,003,695 | `a0611177b6dbd66f72fc43176bed6fe1f6ff91fa0cbcc0116cbe273e2a76d5ea` |
| `sft-math-nemotron-math-v2` | `u002.part0014.jsonl` | 300,015,253 | `d203ffe88589cb5b3042936f695460c4c66ceade5f30251b41e4c6cd858170ff` |
| `sft-math-nemotron-math-v2` | `u003.part0011.jsonl` | 300,004,269 | `836618c7e1c2c7b1a7f739a763d2e35351433e949dfdbeb97639fbb6d4435176` |
| `sft-math-nemotron-math-v2` | `u000.part0014.jsonl` | 300,019,614 | `03da752b0ed224acb8d142549422d4c6f26cc136ea05b80b7025a32b0e812ec4` |
| `sft-math-nemotron-math-v2` | `u001.part0014.jsonl` | 300,117,096 | `21df523dd96e9ed85d9e4ba7f848d26d5a2c7a8710e7948168aa9dcb7dd0cc7e` |
| `sft-math-nemotron-math-v2` | `u004.part0015.jsonl` | 300,004,392 | `4ff1e2e33b681fe838546c9889f4dcf1d2f18f5e23627e9efd218ea2d8cfafb2` |
| `sft-math-nemotron-math-v2` | `u002.part0015.jsonl` | 300,014,198 | `dd778508c20adee8d71986ff80ba19763da3a12169860e06a8b248c2662defad` |
| `sft-math-nemotron-math-v2` | `u000.part0015.jsonl` | 300,008,655 | `7afe6028d230396ec7115dc7538c510c15fc28924f053dc8b5cb6a82b061572a` |
| `sft-math-nemotron-math-v2` | `u003.part0012.jsonl` | 300,002,215 | `79be7ce551470cdc834e1490e9f0449c32b1267eeef485ca242a17f4a6fd20a2` |
| `sft-math-nemotron-math-v2` | `u001.part0015.jsonl` | 300,111,541 | `118853c31833309a84b5adc684fd58ef4eca88c2edf8745e9d1acd94b83597db` |
| `sft-math-nemotron-math-v2` | `u002.part0016.jsonl` | 300,018,182 | `0158ad5379d5f79bae733e7925f3bd865e95f06c94043bfd3f574b0a2f0541a9` |
| `sft-math-nemotron-math-v2` | `u004.part0016.jsonl` | 300,002,892 | `a1a70cf36cad432bcfa035d8beb6d646e92c000f154c9596d4881c853dae3f03` |
| `sft-math-nemotron-math-v2` | `u000.part0016.jsonl` | 300,015,089 | `79157a7dd4aab32e4288d0450bc49905a2b7f886abb6807eb61b1d71d2bcb8a3` |
| `sft-math-nemotron-math-v2` | `u003.part0013.jsonl` | 300,000,696 | `4d7ec883272fc7d8bf447bff4705f485be76c443de16c929995b7e95b12bf5d2` |
| `sft-math-nemotron-math-v2` | `u001.part0016.jsonl` | 300,019,867 | `4b68b7b7921779da132e7b45777f81f5ac82fed200e13674d9f9b19d971c9f11` |
| `sft-math-nemotron-math-v2` | `u002.part0017.jsonl` | 300,017,322 | `ecd7b3c15f4d0058c039a06f1c7d30a24b62670cda76e917450dec49feca7cbd` |
| `sft-math-nemotron-math-v2` | `u000.part0017.jsonl` | 300,033,230 | `55d3e661d9e3389f145d2569bdf1008f1f0fe3e6753d296cf0b8e7269b3b6472` |
| `sft-math-nemotron-math-v2` | `u003.part0014.jsonl` | 300,001,229 | `6225fd65e7918b7683fe347864b6fc7951b6f1eddc53bfa67d14b1c1ec2d71e1` |
| `sft-math-nemotron-math-v2` | `u004.part0017.jsonl` | 300,003,419 | `152975f00bc1033bc6ed9a28c0f660a7e594bbc69ff93390031c4b8b4ee58ae1` |
| `sft-math-nemotron-math-v2` | `u001.part0017.jsonl` | 300,029,474 | `d7d8814a544f85b3311f50b50f46f35e98a8ab49e3a6f3020170fef1dec62cef` |
| `sft-math-nemotron-math-v2` | `u002.part0018.jsonl` | 300,030,343 | `6da9ded2c681d4955c8c2b5dd4761be9db4eb21de0481c3e7ac689cb3daa2367` |
| `sft-math-nemotron-math-v2` | `u000.part0018.jsonl` | 300,025,239 | `5180132dda2fe1b9ff3b9d2625c2449e70dca5d7b0da0906e7599b873129179c` |
| `sft-math-nemotron-math-v2` | `u003.part0015.jsonl` | 300,000,821 | `371f3eee22e04cb7a8715e0151623661fee902cfb6ba91233bb0c58b1b628520` |
| `sft-math-nemotron-math-v2` | `u001.part0018.jsonl` | 300,015,297 | `2fe9ebf53295b1d416d0fad03756280e03f7e4141d7a2a02ef4e5dc48c616098` |
| `sft-math-nemotron-math-v2` | `u004.part0018.jsonl` | 300,012,411 | `34e390a1880d0a95b0ca573244520fefa40a92dc411668f3095a8470bafe7d81` |
| `sft-math-nemotron-math-v2` | `u002.part0019.jsonl` | 300,017,610 | `8eb8ee3972d256a198efbeb99b2201d9618a3a70f4570ac16dd9d8809a1fc9a9` |
| `sft-math-nemotron-math-v2` | `u000.part0019.jsonl` | 300,028,419 | `1e23a57702a147784d9b32dc3f9051b4e67056d3cecbea3a88de0f6fe8cb1522` |
| `sft-math-nemotron-math-v2` | `u001.part0019.jsonl` | 300,163,891 | `79e8705845bdce559b9caabc7dbfc17afee710e2773eb03d47123c15acdffd8e` |
| `sft-math-nemotron-math-v2` | `u003.part0016.jsonl` | 300,003,495 | `3dd3d2412955e739a968f57525153d93b8f6ab43d8cebaa7d6fab33ffad34247` |
| `sft-math-nemotron-math-v2` | `u004.part0019.jsonl` | 300,002,888 | `172c1828af828f8797f5f840a5d22874fcb5da75158c43de2621a750f3fbc810` |
| `sft-math-nemotron-math-v2` | `u002.part0020.jsonl` | 300,007,202 | `0672cb86879e5fc6e2cd9a77619549172d540b3e7b78ffae31a6d7a4386aa851` |
| `sft-math-nemotron-math-v2` | `u000.part0020.jsonl` | 300,016,712 | `865629089d649f2599201a4297c76a56f0c29cf421188741cf7023e674799c4d` |
| `sft-math-nemotron-math-v2` | `u001.part0020.jsonl` | 300,046,078 | `d313255b3b7499b1196663698585e3efb3834397fcce62c07b1eb0486a3f98c4` |
| `sft-math-nemotron-math-v2` | `u003.part0017.jsonl` | 300,001,388 | `0122a59abe638ca75a5fda1d0edfc35f55d761707fb48151394d737a42f3d48b` |
| `sft-math-nemotron-math-v2` | `u002.part0021.jsonl` | 300,030,922 | `6856e6de285485d255ae4b10611c27375df875b2578ec16a0c22142949918f4b` |
| `sft-math-nemotron-math-v2` | `u004.part0020.jsonl` | 300,039,469 | `4ecc71aceaaab6b6db0639230bbfc97304b7ce1110fa056d2e2cf325a519911b` |
| `sft-math-nemotron-math-v2` | `u000.part0021.jsonl` | 300,037,529 | `bf1ac418d9395d0e0b2431c559f35906380f40a328304ddfeedb518c7926b84c` |
| `sft-math-nemotron-math-v2` | `u001.part0021.jsonl` | 300,023,327 | `a11b7382b0a9e8fd57cc8cdc7458686a928e3bac6724f68ab54e825fba37cfa7` |
| `sft-math-nemotron-math-v2` | `u002.part0022.jsonl` | 300,142,910 | `7fe5e9b20c9ba2a9212b1232550a9f45ab0b534336321b8f2fb0bf06b855a0a3` |
| `sft-math-nemotron-math-v2` | `u003.part0018.jsonl` | 300,000,098 | `2b4cf149a7431d16f885e50b7854951620dbe06be33032b5622b8b89008eb7e7` |
| `sft-math-nemotron-math-v2` | `u000.part0022.jsonl` | 300,068,376 | `2e1502d9c40c82ecd598643e7b26c367ed9d760f0d1f48f2cc52daacd80c2420` |
| `sft-math-nemotron-math-v2` | `u004.part0021.jsonl` | 300,018,437 | `f3fd29bd2ea0dd0aeb2c1e664dea2787ca926af75466d56403764c41c13e15a3` |
| `sft-math-nemotron-math-v2` | `u001.part0022.jsonl` | 300,016,810 | `bbaa5f74869a4891119e55ca03b128048a406b395365394421d07efe60263251` |
| `sft-math-nemotron-math-v2` | `u002.part0023.jsonl` | 300,077,038 | `2c8bccc2739e34293bdef649eba2eef5dad0a4a6440e101609f7e73f52b381a0` |
| `sft-math-nemotron-math-v2` | `u000.part0023.jsonl` | 300,035,099 | `e3997b1c4864b1e54ef56e7bd7939daf012eae3d7cd1b984e763f167fdcf7dbb` |
| `sft-math-nemotron-math-v2` | `u001.part0023.jsonl` | 300,145,319 | `6256bb44c334a4a858365e7deb734fa686cc2eb11a928ea3d61fc0abcb8a8644` |
| `sft-math-nemotron-math-v2` | `u004.part0022.jsonl` | 300,025,973 | `f222847ecbacd89f7cac64496797aea1a2e695253fad1c9de28504633fbbebcb` |
| `sft-math-nemotron-math-v2` | `u003.part0019.jsonl` | 300,002,015 | `91178582f5db4c55ccc75ce2f0418f1f432c7c491273f2e0c9c968c2c167db91` |
| `sft-math-nemotron-math-v2` | `u002.part0024.jsonl` | 300,009,449 | `4e34b3d521dfe857128a4d6d02e978761752889b787108b37a55ec162b466246` |
| `sft-math-nemotron-math-v2` | `u000.part0024.jsonl` | 300,008,452 | `1d627b8f6ef90d8730db6947ec0dc844bfcc38441199b2faf71b02ec4b7b73a8` |
| `sft-math-nemotron-math-v2` | `u001.part0024.jsonl` | 300,155,891 | `24597890723ba5c2bb51ec1fa2769a4bf411c2ba1df951e5563bc59690a97281` |
| `sft-math-nemotron-math-v2` | `u004.part0023.jsonl` | 300,009,866 | `28971ce6b8c0017bc1a52d60c18fb0dde59dd8d6b3436757e9469f296530be90` |
| `sft-math-nemotron-math-v2` | `u002.part0025.jsonl` | 300,021,683 | `26206030bea45721d1dbed825a42bfb18c2e01fb5aed16099d8975c631ef1074` |
| `sft-math-nemotron-math-v2` | `u003.part0020.jsonl` | 300,007,162 | `bf1c643ec5afaabd4f25cd96cffccacef24a16be451213684a8adbb08ad88698` |
| `sft-math-nemotron-math-v2` | `u000.part0025.jsonl` | 300,083,835 | `7b08e2cf35a830d9370cb9fb540c3e5147740a28f7ea8403e6ed6399fa1f92d7` |
| `sft-math-nemotron-math-v2` | `u001.part0025.jsonl` | 300,007,819 | `7eca8b4784f55c8dbe4f32310a4bb8e806f83f634fdd23c899de2a0fbcb08c0a` |
| `sft-math-nemotron-math-v2` | `u002.part0026.jsonl` | 300,024,983 | `6c4bf6a36df8da2c91b78d5c86ff0dd0bb85eeb84340a7ac22757871d28d772f` |
| `sft-math-nemotron-math-v2` | `u004.part0024.jsonl` | 300,007,348 | `f94907a4ceed9c0ec4cd31cbed28b4db120299756821f579541bd780c7049116` |
| `sft-math-nemotron-math-v2` | `u000.part0026.jsonl` | 300,001,545 | `46b798ef5739a2b5f2e901f8537eb6ef4ef71f3b2d132d92f70f7f7c9dd919fc` |
| `sft-math-nemotron-math-v2` | `u003.part0021.jsonl` | 300,002,128 | `e6a1bd89943de62bc3310fee088cce4e46ac2d35b544e05077f8f897e608becf` |
| `sft-math-nemotron-math-v2` | `u001.part0026.jsonl` | 300,009,334 | `6ee834941aabed5728fbb7f79d9ed667e5b7610c6d1043d9b923dc33da2b03df` |
| `sft-math-nemotron-math-v2` | `u002.part0027.jsonl` | 300,033,763 | `ab97f5d7e222922f4da4a1942c6a7d59997a3f7f6625eb5b05bf7ad81a528732` |
| `sft-math-nemotron-math-v2` | `u000.part0027.jsonl` | 300,043,101 | `15a190b9320b0fbd2739c8d007589f19c3ed94e3714296e8078e4df9853a2b84` |
| `sft-math-nemotron-math-v2` | `u004.part0025.jsonl` | 300,008,391 | `d3a6d9147b35dbe28a9b14efa24a463f41383e94ef16bb58f79adce79adfad3e` |
| `sft-math-nemotron-math-v2` | `u001.part0027.jsonl` | 300,042,554 | `b7114de7e4c23bbc2526885572dc53b286dc22fa8ab7b28e36715a333694d481` |
| `sft-math-nemotron-math-v2` | `u003.part0022.jsonl` | 300,002,982 | `32be35cf032a6a9a0a5a1b5b2cebac9a318979f405a731275e490e9ea6a388eb` |
| `sft-math-nemotron-math-v2` | `u002.part0028.jsonl` | 300,002,350 | `f5a2436339f3804e0013144c231a13d19bb4236019244f51af17d1bf633a2781` |
| `sft-math-nemotron-math-v2` | `u000.part0028.jsonl` | 300,042,702 | `71f08669f934a7ac2b947d4cf0f27b4fdff9417336fd09e6e7c1c6723ae3be60` |
| `sft-math-nemotron-math-v2` | `u001.part0028.jsonl` | 300,001,806 | `97f54b9f59e68919dc0ffc7efaf9dd4c4eae302e65fe39e55fd50246e93a294c` |
| `sft-math-nemotron-math-v2` | `u004.part0026.jsonl` | 300,003,086 | `b61a65ba7d369aba0fa7f5da17e1d9c5cc66c6fd708b4c0d9eabf604c337c2c2` |
| `sft-math-nemotron-math-v2` | `u002.part0029.jsonl` | 300,002,341 | `6bc235d3ad2358ed9b8ff52dcac7b5b9c3fa784b8690f2ed3db7ebb15ee015fe` |
| `sft-math-nemotron-math-v2` | `u000.part0029.jsonl` | 300,015,593 | `6f72e63c61328c64a6cb59dd7f25be92c5cc0eeac96eec7a30a5beaba51eea3f` |
| `sft-math-nemotron-math-v2` | `u003.part0023.jsonl` | 300,004,420 | `d6237d7a458b418337bbb5b464207ee78bc9ba5985343a3e8539fd0e5976c08f` |
| `sft-math-nemotron-math-v2` | `u001.part0029.jsonl` | 300,055,690 | `36eb10517f95f7bde3bf94e3e85dc30dac47cba39ad5a799412766fd792dc475` |
| `sft-math-nemotron-math-v2` | `u004.part0027.jsonl` | 300,045,842 | `d116e64b94e0fb2d0dda1bc164c970882e8716b0c4a589927a8df5d5a283cba4` |
| `sft-math-nemotron-math-v2` | `u002.part0030.jsonl` | 300,001,763 | `b01457c6c3bebfc3183032f5116f3cecf3a45f33396d9dc1d3fb222d81a61a5c` |
| `sft-math-nemotron-math-v2` | `u000.part0030.jsonl` | 300,011,614 | `11b2fa14174818a826950ad5d0b803e61fb9968945138c4084db34d53cce70e8` |
| `sft-math-nemotron-math-v2` | `u001.part0030.jsonl` | 300,005,732 | `77fae41e036c1248f354ab1f5eab7aa910e65cb7345ab6ac55f48c8aeba0ad6f` |
| `sft-math-nemotron-math-v2` | `u003.part0024.jsonl` | 300,003,544 | `75ca9cfada9062f4d3e6b8d88d8a510dcba88292c8f7a3650f4f8f126b393248` |
| `sft-math-nemotron-math-v2` | `u002.part0031.jsonl` | 300,018,712 | `41b754d7c47afb10ad6aba707b343634a4e61a96e3b973893ee699656e9d23bc` |
| `sft-math-nemotron-math-v2` | `u004.part0028.jsonl` | 300,005,156 | `613dd48e150937fc93b46149ae7402624c43f9513415d240aab44a74a5424450` |
| `sft-math-nemotron-math-v2` | `u000.part0031.jsonl` | 300,034,160 | `4bf91498551d6ce6ba8bc425c5f031aa88926dd2bba4ea8a1a455588b4358237` |
| `sft-math-nemotron-math-v2` | `u001.part0031.jsonl` | 300,111,620 | `21933d6ab364119ae6d9777634ae9d3b7340b127db6a1488d446f20dd68fb400` |
| `sft-math-nemotron-math-v2` | `u003.part0025.jsonl` | 300,004,914 | `1e81994ace2c7f802e948a860f2c847a3c74343576015385e7336d2796bb8b2a` |
| `sft-math-nemotron-math-v2` | `u000.part0032.jsonl` | 300,049,395 | `5b8127ba68c58803476eb16b2f6364a6fbecda168b954295c9bab63139a47b6c` |
| `sft-math-nemotron-math-v2` | `u002.part0032.jsonl` | 300,012,893 | `aeafad595496a0d7dfe38e8635570703bf2e25797ac819e732b527f0a41b46c7` |
| `sft-math-nemotron-math-v2` | `u004.part0029.jsonl` | 300,007,948 | `68e7b2e2a528ce53a776a4e43098a6b227e578501b0cd1d8b32d96392063cc1c` |
| `sft-math-nemotron-math-v2` | `u001.part0032.jsonl` | 300,061,953 | `447d3313108c5e008440809a9d343e5f9b653202856a7a1f2c10a7c92f61a37e` |
| `sft-math-nemotron-math-v2` | `u000.part0033.jsonl` | 300,012,485 | `39ac12d30efaaff7dbce4f81513a39f720cdee545e84dd65ad826c7bddfc52e3` |
| `sft-math-nemotron-math-v2` | `u002.part0033.jsonl` | 300,001,960 | `e9fb2e6b76b041d4957590b39b1ce968d65350abddeab288e5d9989077664dd0` |
| `sft-math-nemotron-math-v2` | `u003.part0026.jsonl` | 300,000,025 | `8f64667327190cac4df0dc45d9151815a52ee7240c8ab669479c0c14e44cb84b` |
| `sft-math-nemotron-math-v2` | `u004.part0030.jsonl` | 300,012,706 | `3a967cfc2702212f8a702bd481873dcc51fa1edf301c8e657b2cecfb153804f2` |
| `sft-math-nemotron-math-v2` | `u001.part0033.jsonl` | 300,014,618 | `fc3171337cff13a20e4f75f1b130f38103e8ae5f9ce8a26945d9d85749e46a99` |
| `sft-math-nemotron-math-v2` | `u000.part0034.jsonl` | 300,023,387 | `3d220738e5fd58ffa56e134c358c5c14fa042c4d4fae3340277d62e50ebf03f4` |
| `sft-math-nemotron-math-v2` | `u002.part0034.jsonl` | 300,054,891 | `3b9ecc7c505f8224be078237bedd6078c0a6f52a09b73dbdc23a6d3b88acf7f2` |
| `sft-math-nemotron-math-v2` | `u001.part0034.jsonl` | 300,020,674 | `e324c78c4e21d1ffdd1ef6122403754e008ab102772d6bf9eb844103c8ca7845` |
| `sft-math-nemotron-math-v2` | `u003.part0027.jsonl` | 300,008,029 | `58943984c40a8e58e3f2abfa08c1c0e1261bb57bd02b63fdddd3bb40114e10e9` |
| `sft-math-nemotron-math-v2` | `u004.part0031.jsonl` | 300,002,399 | `68a4cd95667010f7f6c2cb97aebc4418aec5ad3eff7d0ffcb4d2af40e0bfb038` |
| `sft-math-nemotron-math-v2` | `u000.part0035.jsonl` | 300,041,384 | `6907447a7b1b8bb1e96b4615c0522ad82a3068980ada8e1e9296aa4e49e102f9` |
| `sft-math-nemotron-math-v2` | `u002.part0035.jsonl` | 300,011,836 | `603beb1ba5bd34699ad05c32b5db0a28e117c15ef3e292508b7f7bea05ef4cf0` |
| `sft-math-nemotron-math-v2` | `u003.part0028.jsonl` | 201,474,933 | `0314c589cd7b11ee5bf8b3b2c440a15de730246b9b250500055909922801df54` |
| `sft-math-nemotron-math-v2` | `u001.part0035.jsonl` | 300,000,860 | `48e9c972d99e74339c62bc57ed344a9c1c1e1657b996e30f4b58c36c89592a9e` |
| `sft-math-nemotron-math-v2` | `u000.part0036.jsonl` | 300,105,148 | `95e970c6ca10f873c823b2f82b0d97dd282958916fe53d07b0f0e164c22439af` |
| `sft-math-nemotron-math-v2` | `u004.part0032.jsonl` | 300,001,698 | `f17df65a5a781ad2324b720178e67368a8f04d7f539fd0438ef63593d80a4238` |
| `sft-math-nemotron-math-v2` | `u002.part0036.jsonl` | 300,027,181 | `8458cc93f6c6a0eb83a2b618abc384bf0e8da33e0200dae73a0e830c3f8b5cdf` |
| `sft-math-nemotron-math-v2` | `u001.part0036.jsonl` | 300,000,506 | `a3f90fbc5ddaac65ce2808b443bb70203e1e3f6b7a7fd5caffa75701c73b21df` |
| `sft-math-nemotron-math-v2` | `u000.part0037.jsonl` | 300,007,485 | `fc7caa1899a4bdd7f9c130745d3cbd69bfe0dd7808886564b8705ebacb4fe07b` |
| `sft-math-nemotron-math-v2` | `u002.part0037.jsonl` | 300,028,738 | `a6634194cb3b3071f8c6834348573bd8d6653eec14ae9043fd177db8404eb45a` |
| `sft-math-nemotron-math-v2` | `u004.part0033.jsonl` | 300,022,510 | `9228d4c1af64c91dd0903c2079643ae4ec1873cec3dc2a20f301d19add4af6fe` |
| `sft-math-nemotron-math-v2` | `u001.part0037.jsonl` | 300,032,989 | `0e40aceeedb8194019d0b575fc84f19abb72fd126327c7e96c2a564dffadfc8b` |
| `sft-math-nemotron-math-v2` | `u000.part0038.jsonl` | 300,175,641 | `44d18396e3ef951616d29d5845e46f5af61e0d97968cdcb6a7407d2848658c68` |
| `sft-math-nemotron-math-v2` | `u002.part0038.jsonl` | 300,001,413 | `4ca249ae88e970e578913424b96d967ce69a8da2e6a78dd196b6b1e1d6259e36` |
| `sft-math-nemotron-math-v2` | `u004.part0034.jsonl` | 300,016,852 | `f4e9274fddb38f388d7e3763f73485aa77bc64b48887b4c0a3117b4886202a39` |
| `sft-math-nemotron-math-v2` | `u001.part0038.jsonl` | 300,033,048 | `7fb5c52b0abb1a7104f3d67d351a974918667ff2ee4d2015e0ed27509d6524ba` |
| `sft-math-nemotron-math-v2` | `u000.part0039.jsonl` | 300,002,972 | `9d77469f0660406eff1816c2d56f4df5ff7b06b5f56fc67aade93e2fb4696ecb` |
| `sft-math-nemotron-math-v2` | `u002.part0039.jsonl` | 300,153,023 | `e83b12229da5828493f9a0fbd5f71e84c5edc2e8535f1918bfa29252fb721e71` |
| `sft-math-nemotron-math-v2` | `u001.part0039.jsonl` | 300,004,309 | `9c7907395ac9d0ff44fc99ebe219951f07ee2947474d242964d2a5e72588f83e` |
| `sft-math-nemotron-math-v2` | `u004.part0035.jsonl` | 300,017,226 | `b0d39163925e9eb48ed78e3522d0b1cc93cafb9bdc2068c83cd206194aa3fff0` |
| `sft-math-nemotron-math-v2` | `u000.part0040.jsonl` | 300,022,978 | `cec994308388b3be0936b293cea4e891553381e09afba7e6d6dad03fbbe6a636` |
| `sft-math-nemotron-math-v2` | `u002.part0040.jsonl` | 300,064,946 | `c676bb6f2e08494ac8617c687e4d177904727edfee0d0c0673790c293c17a68c` |
| `sft-math-nemotron-math-v2` | `u001.part0040.jsonl` | 300,014,476 | `4ef55ee539c78f45f956a2c9a9847a07875b61bb7b80f42ad499a94dc68dd1dc` |
| `sft-math-nemotron-math-v2` | `u004.part0036.jsonl` | 300,001,520 | `e2a5b6b985d31cbb53386661b55febd3500fd1aa6b45b8dd9913eabbd8e65b10` |
| `sft-math-nemotron-math-v2` | `u000.part0041.jsonl` | 300,064,311 | `871e16f6e7b59b9321a181175c5cb6d94a95bd57193e63105b810e46e1dbc6f6` |
| `sft-math-nemotron-math-v2` | `u002.part0041.jsonl` | 300,056,885 | `d272691ee995d3a2b9012627eb225b24dc96f9da167f2931b92e2241af695f05` |
| `sft-math-nemotron-math-v2` | `u001.part0041.jsonl` | 300,035,913 | `c6584921868fe3266ab635421e28a3f7a692dd58abb43f640ae0b29846072ef3` |
| `sft-math-nemotron-math-v2` | `u000.part0042.jsonl` | 300,210,149 | `ed45156c3002a7193ea31c1c203b78896aa94b8f0bbd48482e7346839944e6de` |
| `sft-math-nemotron-math-v2` | `u004.part0037.jsonl` | 300,000,667 | `00e0dfc76eedc12243305aa5a16c3cd4adbd9d96e318a8a5785dceadc6382bca` |
| `sft-math-nemotron-math-v2` | `u002.part0042.jsonl` | 300,022,459 | `7065fafdca2cbbae3d0613a9e0ffd3d17927d823f1c6fffbae35eea714d26dfd` |
| `sft-math-nemotron-math-v2` | `u001.part0042.jsonl` | 300,011,793 | `2c6ed57d858628486ada9d1fb00955509bf0a32b90badb7dcfdd7d815e423000` |
| `sft-math-nemotron-math-v2` | `u000.part0043.jsonl` | 300,016,168 | `bb515abc07e3a685e8d3b30653756d570995d0a9edff0524c4920d4c955dfd68` |
| `sft-math-nemotron-math-v2` | `u004.part0038.jsonl` | 300,001,881 | `7d8d58b601e166aad404801eacde6016c4c80842a742bb0a6adae92a7bad1221` |
| `sft-math-nemotron-math-v2` | `u002.part0043.jsonl` | 300,004,428 | `01ea8e88d53a5a7f8a5f9f5467d532e86b2dbfce1661419d9368e9b10d071eb4` |
| `sft-math-nemotron-math-v2` | `u001.part0043.jsonl` | 300,004,371 | `06c096ac11c0b008ed6d3de30f9ac1df4d1d36233ab90a436100ef42a9a9388f` |
| `sft-math-nemotron-math-v2` | `u000.part0044.jsonl` | 300,020,135 | `230166906117595b77b751d263f6c5eab587ff694f6ef8f3e4ee740d9732a4df` |
| `sft-math-nemotron-math-v2` | `u004.part0039.jsonl` | 300,005,062 | `2c79f5f24934b8bb296fb9f1637f9163e9977439e4a43776e85896cb5135d8db` |
| `sft-math-nemotron-math-v2` | `u002.part0044.jsonl` | 300,014,879 | `cdac0a9485d5f5f3ae0fdbba0388e094265244abd720f7fe1b7b91183ac9427e` |
| `sft-math-nemotron-math-v2` | `u001.part0044.jsonl` | 300,026,348 | `606400b5046c5c0cd79ea8c5a420a560e35a395a6e7a66728e9d34e964678df4` |
| `sft-math-nemotron-math-v2` | `u000.part0045.jsonl` | 300,037,769 | `34620ef13099006451ae9ea31b5e230eacf2890d39e71b268c519955cbd01333` |
| `sft-math-nemotron-math-v2` | `u004.part0040.jsonl` | 300,003,992 | `e181c966da5dd547c93fc9f0c9883a5483b98be0e7c4cdc5be4e7362076d4727` |
| `sft-math-nemotron-math-v2` | `u002.part0045.jsonl` | 300,007,947 | `88152cbe75d98fd6ac1f4cc6ba5fd7de0951f973bf7eea164ef928b01ee64660` |
| `sft-math-nemotron-math-v2` | `u001.part0045.jsonl` | 300,110,125 | `d37e24f78a29e28da78e60a501341364239c2bc4d15077de5b35b85c60e8fbee` |
| `sft-math-nemotron-math-v2` | `u000.part0046.jsonl` | 300,057,911 | `7f1d5d5f49a0e560c109212bf020b13bd7b23ad92099e33725ad70bae11d6f83` |
| `sft-math-nemotron-math-v2` | `u002.part0046.jsonl` | 300,018,675 | `6ea7e6eb541a19f754ecb117e8da932488ac5857fdd76be1ba34cd1449c1d5f6` |
| `sft-math-nemotron-math-v2` | `u004.part0041.jsonl` | 300,002,492 | `43d96617be1381397e7ce20b3a8a998506246efc0c4d9b19af6f00d480111af1` |
| `sft-math-nemotron-math-v2` | `u001.part0046.jsonl` | 300,068,681 | `cf2ca07eb8b549081ec1e217bb0a56a9a3197a3c48e5c6d677cd9396226d9f96` |
| `sft-math-nemotron-math-v2` | `u000.part0047.jsonl` | 300,048,340 | `5dc55cc4ee29739f5ede3d67be47201a4efbaa7cdfbc9a11098f54aeb4357fd7` |
| `sft-math-nemotron-math-v2` | `u002.part0047.jsonl` | 300,018,373 | `ebbe2d6ab35bffcc09f6aded360335fa6d7d2199514f8273799970eac0f9381b` |
| `sft-math-nemotron-math-v2` | `u004.part0042.jsonl` | 300,007,931 | `5378527dae06e6ff61e3226416b468309612234f770cfed8c8e177cb8421c874` |
| `sft-math-nemotron-math-v2` | `u001.part0047.jsonl` | 300,041,632 | `4f64d0630546f84d92908ac07d68ee5e19329b391e5e6f204beb8682945424c8` |
| `sft-math-nemotron-math-v2` | `u000.part0048.jsonl` | 300,015,019 | `b2b4122203f2880a2fe47f287e0b141385dec2361c1d43240a7bdeed22f77bec` |
| `sft-math-nemotron-math-v2` | `u002.part0048.jsonl` | 300,005,397 | `72a89288fdba97b16932378ef110f511a08b9bb016d5cc6935b1f72f935ec2ce` |
| `sft-math-nemotron-math-v2` | `u004.part0043.jsonl` | 300,010,029 | `8dd7e3da031404e312d06b86871a4a558a462fa77ee64f339a885d4e3c29691f` |
| `sft-math-nemotron-math-v2` | `u001.part0048.jsonl` | 300,011,172 | `7b15897f32ce10b105b85f89e436a90fb2ce3b9f780711f919e60e95cbe00400` |
| `sft-math-nemotron-math-v2` | `u000.part0049.jsonl` | 300,093,566 | `70140e04d4973b605593227bfe1e4449185cc7018c3540180a08cc4b870c81e9` |
| `sft-math-nemotron-math-v2` | `u002.part0049.jsonl` | 300,161,935 | `7e00a8fa60f0e9a78fa4ddc75d5f8714b8640c6cc653916b3d94f74e7ac07364` |
| `sft-math-nemotron-math-v2` | `u004.part0044.jsonl` | 300,010,033 | `624a79314f394c0cfd134b6af7685f2f888aa98b0ce9888974dfae3d97869d89` |
| `sft-math-nemotron-math-v2` | `u001.part0049.jsonl` | 300,007,463 | `1738ffb0202596bfad07866f327ddaca32bced4835a5b52a0a7cde4e36e09c01` |
| `sft-math-nemotron-math-v2` | `u000.part0050.jsonl` | 300,050,364 | `19fd5521837e3317afcd6970b673941f8f795c16f0deb8c74b98e3981c97ba81` |
| `sft-math-nemotron-math-v2` | `u002.part0050.jsonl` | 300,008,230 | `35c94830587515297640ce53175e1ea30da2d5e4c0917ce93bf14bfdc3e247b6` |
| `sft-math-nemotron-math-v2` | `u004.part0045.jsonl` | 300,004,344 | `9ab317b936525ddfa13ac0298d07657bdfeccde747bab323d7098e43c9121726` |
| `sft-math-nemotron-math-v2` | `u001.part0050.jsonl` | 300,015,448 | `054677920370f4c9e65afcee71e7ba59f982c4bdef017bfb9d6cb6209c48205f` |
| `sft-math-nemotron-math-v2` | `u000.part0051.jsonl` | 300,012,251 | `8e165a7d823d99c19ce5e67229248862ccf15ea11627244a67ae71450b94edfb` |
| `sft-math-nemotron-math-v2` | `u002.part0051.jsonl` | 300,007,876 | `ad276e51300d194c459d20ebb2eb2b88088622988c0b2f935d43b30258c923ea` |
| `sft-math-nemotron-math-v2` | `u004.part0046.jsonl` | 300,001,924 | `c8ebfce90f5329119b886fab0c4c652a5d383e71e98f7adb377cf75ac0adec31` |
| `sft-math-nemotron-math-v2` | `u001.part0051.jsonl` | 300,006,771 | `de9128fe12faca37fe6c209cfae852e5d53e6025c19b629e9c3f28934c670ead` |
| `sft-math-nemotron-math-v2` | `u000.part0052.jsonl` | 300,096,153 | `0e86972a89d7444cdbffd3b4d3fd6649bcedd34529abf086b9dc0e0422b0f3ac` |
| `sft-math-nemotron-math-v2` | `u002.part0052.jsonl` | 300,013,637 | `5431582f4801b35433c4b118b7e0ecb16d097ddc7c36acf45cb8840f4e34ed80` |
| `sft-math-nemotron-math-v2` | `u004.part0047.jsonl` | 300,010,274 | `b833a4b27ee01cd355df4e3267950acc1795101065c347ff1ef55da20c61d392` |
| `sft-math-nemotron-math-v2` | `u001.part0052.jsonl` | 300,044,421 | `b7eb493037cd8ee8d219a0b76883da3888f84bd78c6a949fd68a72e49ea29168` |
| `sft-math-nemotron-math-v2` | `u000.part0053.jsonl` | 300,006,662 | `33d2a387e670a318c181bd3b6b54ee901a1f8ebc71e53c4b8184886cfd8653b9` |
| `sft-math-nemotron-math-v2` | `u002.part0053.jsonl` | 300,131,835 | `18abefe0e7e75cc919cffddb560ae337c66b0f6360ca794815379f83722f0fdc` |
| `sft-math-nemotron-math-v2` | `u004.part0048.jsonl` | 300,009,886 | `11f1735093ab62fa737823e025dcc058a45f94b4d1d6a60a978e6a93b95880ae` |
| `sft-math-nemotron-math-v2` | `u001.part0053.jsonl` | 300,007,751 | `a9c7f9731920168a75025b4d249436b17e3ac1620ea649557df47dff3c151673` |
| `sft-math-nemotron-math-v2` | `u000.part0054.jsonl` | 300,061,627 | `2b2d4a3c0740fce71db6e4632349fc53f01a9a97635f98887a7ab49fdecdb112` |
| `sft-math-nemotron-math-v2` | `u002.part0054.jsonl` | 300,013,872 | `37a367b1a401e1db7124766e1497f3c554cfb27bfa7fb2a015af4afd16496c78` |
| `sft-math-nemotron-math-v2` | `u004.part0049.jsonl` | 300,008,411 | `561e391f6da4431c33a9e27ee7cf14f19e6d5e4908b14db1fe8261d4666b0293` |
| `sft-math-nemotron-math-v2` | `u001.part0054.jsonl` | 300,012,714 | `4982fee54affc59b51093e9308ad9ef1bdbe1a5c6cc98a660fba82bb95314884` |
| `sft-math-nemotron-math-v2` | `u000.part0055.jsonl` | 300,004,508 | `d94ca8482b2d2c16190eb498992f78e51e93a52be066088f728e119bc76c8cf9` |
| `sft-math-nemotron-math-v2` | `u002.part0055.jsonl` | 300,021,658 | `f10f46fb8dcb2470ac258f2a635ab82cca57d9cc63a78f76febccde81dbc7267` |
| `sft-math-nemotron-math-v2` | `u004.part0050.jsonl` | 300,000,950 | `ba8622878cd36b692be7f09ad8e2453b7083368457efb36a34321d9261d09e60` |
| `sft-math-nemotron-math-v2` | `u000.part0056.jsonl` | 300,056,443 | `74a34b1800a17a4b6998afd5a3301feacb0a09a53d2aa32b5bbc3df272428cc9` |
| `sft-math-nemotron-math-v2` | `u001.part0055.jsonl` | 300,037,993 | `2bea12d94f14ca0600e6f21ed12f324571a53cbf695837579ed11da59ad949d9` |
| `sft-math-nemotron-math-v2` | `u002.part0056.jsonl` | 300,038,606 | `363febb551f7c60af27ac6d5133336c2f15e96e0fa0eff5c183fcdf2b3451c05` |
| `sft-math-nemotron-math-v2` | `u004.part0051.jsonl` | 300,002,632 | `5e4f74f6eb2fa11535c53823c9d232ac551ac9dba95394a6ed797508c88d1644` |
| `sft-math-nemotron-math-v2` | `u000.part0057.jsonl` | 300,057,595 | `966547d1c494347201bf339787ccbc553d7457f25391b6c2e6ac51c360542ba3` |
| `sft-math-nemotron-math-v2` | `u001.part0056.jsonl` | 300,016,387 | `792f28f1c1fafb842f90e36a439f22ce78b5ac062a03d9ad76acd9e50495fe80` |
| `sft-math-nemotron-math-v2` | `u002.part0057.jsonl` | 300,072,443 | `39749f6218cdae5f5eba6cdd090a5889c41a41bc91de08154cadea6b08e51a29` |
| `sft-math-nemotron-math-v2` | `u000.part0058.jsonl` | 300,012,387 | `21e73fef7fb70a5bc5d8267404c361b5ff3cb620ce25a983af83316b196ed29a` |
| `sft-math-nemotron-math-v2` | `u004.part0052.jsonl` | 300,013,380 | `e332fa1d75c77d89973ddd533e3d1bd6afdbb175ca811e9cc06adbbb3476932e` |
| `sft-math-nemotron-math-v2` | `u001.part0057.jsonl` | 300,019,153 | `1d26a336b2a6a3f1b16423c48575855bcd18d393f0791226827e9d2726e267b1` |
| `sft-math-nemotron-math-v2` | `u002.part0058.jsonl` | 300,012,916 | `4e7bdf65ac6387f758f5c03514ba6bf2127dee90859c3189fe325fce73744a7d` |
| `sft-math-nemotron-math-v2` | `u000.part0059.jsonl` | 300,092,185 | `438a117909deac95bce78c881bd0a0210f2a98633fc39db15c1a99a883b33baa` |
| `sft-math-nemotron-math-v2` | `u004.part0053.jsonl` | 300,002,045 | `70b18b1bea90597f552bed1bd4210794cffe89d5f1eec3a84b334746da1425ca` |
| `sft-math-nemotron-math-v2` | `u001.part0058.jsonl` | 300,085,923 | `eae04b09dd548867d0944bde34e5c65cf51db2812d254cd98281c155309c28d5` |
| `sft-math-nemotron-math-v2` | `u002.part0059.jsonl` | 300,005,630 | `b620794b947f83b65cc4bb71a564c0348815de4b454d4016623ebafb9bd63f19` |
| `sft-math-nemotron-math-v2` | `u000.part0060.jsonl` | 300,055,267 | `0202fa4ca1e293598ad2916581abccf84cdef94ef306f808a4ca258bcb28b43a` |
| `sft-math-nemotron-math-v2` | `u001.part0059.jsonl` | 300,037,791 | `b8b94d1b7def206089918abbc801048e5e7740b5c00d1e4071b18f6cb281dfa7` |
| `sft-math-nemotron-math-v2` | `u004.part0054.jsonl` | 300,006,674 | `65c65c14b26f632bbab6f7db14008884e04db723984473b6a94fff5b4980c31b` |
| `sft-math-nemotron-math-v2` | `u002.part0060.jsonl` | 300,071,100 | `865ef0713c00de98c72c1a3fb44a0ae816afce9a351f05c71cd3a17aff76c0f5` |
| `sft-math-nemotron-math-v2` | `u000.part0061.jsonl` | 300,115,306 | `57698401e9fedb556989c8ef00ba5b3ed31321190158f4789fa940038a78d0f6` |
| `sft-math-nemotron-math-v2` | `u001.part0060.jsonl` | 300,047,937 | `78852fa8dacf2f42f55e0851d00c495072f7ece239d68a1085efafe727e7e827` |
| `sft-math-nemotron-math-v2` | `u004.part0055.jsonl` | 300,000,306 | `fcf932611116f9e67c10ad9f12ffe33684d6550ee7b25d996d26ff10606ca020` |
| `sft-math-nemotron-math-v2` | `u002.part0061.jsonl` | 300,020,094 | `edc0d7ab1ce4e5c62463b19baf6f8abddf4278e76aa89e1563d5f8148dcf2f4b` |
| `sft-math-nemotron-math-v2` | `u000.part0062.jsonl` | 300,071,221 | `f289ad6e1f05dcac0cec10b18fe3b88d91328ffd716ab3252004ccb98f38470d` |
| `sft-math-nemotron-math-v2` | `u001.part0061.jsonl` | 300,045,408 | `d9d1f8ddb98556e95c34a2a6b8f0d3411e661dbbfd022956fbebc90dc08fc70d` |
| `sft-math-nemotron-math-v2` | `u004.part0056.jsonl` | 300,001,638 | `f0935f3fa305e29d69a6a540e31f1739a56aa62f5dcf0049bd744ec07afecd8e` |
| `sft-math-nemotron-math-v2` | `u002.part0062.jsonl` | 300,016,740 | `2b6d094ffa1180d2a996706742db5bf31b331a3b9407b256dbf2bbc3051342e1` |
| `sft-math-nemotron-math-v2` | `u000.part0063.jsonl` | 300,031,923 | `68a04cf397ecc68e8fa1569815e1ddd8869df83c095d246935596171153b16df` |
| `sft-math-nemotron-math-v2` | `u001.part0062.jsonl` | 300,021,443 | `de37438f36f72fce9d42c19378cfed56919da2822281f102cc042049e2597feb` |
| `sft-math-nemotron-math-v2` | `u004.part0057.jsonl` | 300,006,069 | `e0a8d170e9590883a87b4b4fbaa193b3d5007c905798e6582ce8ab27da68650a` |
| `sft-math-nemotron-math-v2` | `u002.part0063.jsonl` | 300,012,657 | `e1e3377a54e83373cc54029c31a0df171d5af9d9ce59276181b510a9e887314c` |
| `sft-math-nemotron-math-v2` | `u000.part0064.jsonl` | 300,031,238 | `ecebbb4ef4ef5c922c678d536e29ed0d69f846233df6f307a59b8edbf23bea7f` |
| `sft-math-nemotron-math-v2` | `u001.part0063.jsonl` | 300,004,585 | `96beeb6416fcd9ed9eafbd653afa0fd2746ed11a0207f85af4bea6b467b23d27` |
| `sft-math-nemotron-math-v2` | `u004.part0058.jsonl` | 300,000,760 | `d7c4ce2986a79618ffee9aff8d8e82a4b0461f3238a6839849918a37591131b8` |
| `sft-math-nemotron-math-v2` | `u002.part0064.jsonl` | 300,004,677 | `95abfa1d4616013dae02a1062b0ea1f8338a6d9355b45fd18562a2d2eb4e62a3` |
| `sft-math-nemotron-math-v2` | `u000.part0065.jsonl` | 300,143,053 | `3dcf7ca65105243ada2b9b9407d24e4a5dc64c9285e1e05229a7abe163cd0db9` |
| `sft-math-nemotron-math-v2` | `u001.part0064.jsonl` | 300,060,108 | `5c49d46d85bc2238efdf9974ab48b3185890e673313d2da7cc1b4a1f0ee292d2` |
| `sft-math-nemotron-math-v2` | `u004.part0059.jsonl` | 300,006,526 | `046303a5a418c01a6084afd433d67e8ba6073c6624514249ab2d324a81225d03` |
| `sft-math-nemotron-math-v2` | `u002.part0065.jsonl` | 300,009,638 | `3d0ab6b21bae2ca63e808a55a08896c7164f0897109fe79fd1c5081fc3739e61` |
| `sft-math-nemotron-math-v2` | `u000.part0066.jsonl` | 300,009,024 | `0dbbdee04b47063387c2193923da9154c2af1b0bf9f85cd7bb6e6d6768e58165` |
| `sft-math-nemotron-math-v2` | `u001.part0065.jsonl` | 300,011,097 | `f399e4f4c9642fa8bcc9f1becbcf8c944f555a1dd34ce4a142e6cb87bd35b9df` |
| `sft-math-nemotron-math-v2` | `u004.part0060.jsonl` | 300,000,910 | `e2f76a6643b243018e187765ac0600815c5fa69bd9d03f9d022e15b0bf8a1041` |
| `sft-math-nemotron-math-v2` | `u002.part0066.jsonl` | 300,070,545 | `9e5a372d6636785c2d6502bdcdbd0276dd9808a1ba91f1b0c1f58ccca76cbc11` |
| `sft-math-nemotron-math-v2` | `u000.part0067.jsonl` | 300,003,970 | `2ca82092d450642f3561c3b4c4cbd0da935dfb155589d1afe48e19fbf5bd1245` |
| `sft-math-nemotron-math-v2` | `u001.part0066.jsonl` | 300,079,525 | `585ae93e83541e7953450fb71e51dda13a6753470e791ac2262d214cf7d72216` |
| `sft-math-nemotron-math-v2` | `u004.part0061.jsonl` | 300,006,294 | `91cd56a259554ec0de5349d816e96a0859b80f10c1030b92e50ecc12cc8dc089` |
| `sft-math-nemotron-math-v2` | `u002.part0067.jsonl` | 300,016,934 | `a6d66c18b8a6fede1b9975e702fd4c03f827902fc51ee11994d1ad5c2d69c29b` |
| `sft-math-nemotron-math-v2` | `u000.part0068.jsonl` | 300,035,876 | `590d51f4a87058539e16cba5915e9894646e23282ca31819251bf684a971be9c` |
| `sft-math-nemotron-math-v2` | `u001.part0067.jsonl` | 300,039,628 | `41d219cbc48a3ee7f22dded41316fb110b9059d5087c9f46a7f1751390264f13` |
| `sft-math-nemotron-math-v2` | `u002.part0068.jsonl` | 300,000,480 | `f91f63ab6ddccec862f511bdc9ef8a9d5a19f7bc4716cd016fa41f3cf55ce3e1` |
| `sft-math-nemotron-math-v2` | `u004.part0062.jsonl` | 300,014,653 | `e6be4eedfb98b6c647ea1386e796d6830a2c6f82db517d47016e9405879dfdd1` |
| `sft-math-nemotron-math-v2` | `u000.part0069.jsonl` | 300,010,759 | `9d210a55dff93a418202d1bcc0c2d942756ecba5cd77c8ebf13658e377dadc07` |
| `sft-math-nemotron-math-v2` | `u001.part0068.jsonl` | 300,062,122 | `667f055ad97ce889d4b54799ae1506c5131c567a252b598fef3416a1907dda41` |
| `sft-math-nemotron-math-v2` | `u002.part0069.jsonl` | 300,005,369 | `9394622aa1578e2c24c27798ed64a83f5712632cc1a68710245196f8b2bd2ace` |
| `sft-math-nemotron-math-v2` | `u000.part0070.jsonl` | 300,048,958 | `5ae5b9231d78483d9035e38e0ee58190d31edf313909acf43d32667b17c383af` |
| `sft-math-nemotron-math-v2` | `u004.part0063.jsonl` | 300,020,077 | `198470812885ab5e1ebe7b87d4938e286a81c796cbff4de524fb253763c1537c` |
| `sft-math-nemotron-math-v2` | `u001.part0069.jsonl` | 300,003,232 | `ad439909bbdf6c7c222412f894bc3684fa1292392d987b40f262f07a05df0b1c` |
| `sft-math-nemotron-math-v2` | `u002.part0070.jsonl` | 300,036,251 | `18ed2a06f927047488599f611743ce4d939507c3571f1d889551ac23940ac220` |
| `sft-math-nemotron-math-v2` | `u000.part0071.jsonl` | 300,008,760 | `74a654ce276495afb3c54ca2a9bd2bde1050eb1ea661a88e6e8816be39b234f2` |
| `sft-math-nemotron-math-v2` | `u004.part0064.jsonl` | 300,002,958 | `c4bb281c8d6be65b239483948d4ad716a1128dc85e5c37a14cb52ee79f529293` |
| `sft-math-nemotron-math-v2` | `u001.part0070.jsonl` | 300,064,906 | `5525e42bca22dab947b66bf0759a8ca4a67ce52609cd1b0e656042db135429eb` |
| `sft-math-nemotron-math-v2` | `u002.part0071.jsonl` | 300,010,641 | `4e5135e02bd7795deea45ec56f5f7dc972fa096be2452d23cb36db06555c8e9b` |
| `sft-math-nemotron-math-v2` | `u000.part0072.jsonl` | 300,097,817 | `2ce419a12293e14eef5a53c0282d0dc63594a17990876ed06180f6c0863c2808` |
| `sft-math-nemotron-math-v2` | `u001.part0071.jsonl` | 300,077,727 | `25f7678b668d14e3a84491f3851262d532fb569cf448aec0087f376f4504e9a3` |
| `sft-math-nemotron-math-v2` | `u004.part0065.jsonl` | 300,005,048 | `630e4ee32f2d41c59d8c12350d240ffc6e30ef2d6034c77b50be270762bdd957` |
| `sft-math-nemotron-math-v2` | `u002.part0072.jsonl` | 300,021,383 | `ddda69e87e351cb03b20b4e6112b9e64e85647efeb4f05813f2cd1fbd90d9250` |
| `sft-math-nemotron-math-v2` | `u000.part0073.jsonl` | 300,016,238 | `b2e47455d36322dbddc15c50fca5b77277de49ad71632241177efdf5e837dfeb` |
| `sft-math-nemotron-math-v2` | `u001.part0072.jsonl` | 300,013,653 | `be0ce3a0f6ba4dad9cf6a5a4532ce60a7dc0019ab797d8c7b3a200562210ebc6` |
| `sft-math-nemotron-math-v2` | `u004.part0066.jsonl` | 300,004,558 | `05fff6c92ce72e21d5d65cec98347028c84c39ad3e2b8b813c6a5a6922a6bc0f` |
| `sft-math-nemotron-math-v2` | `u002.part0073.jsonl` | 300,042,694 | `8bcccc503cf4c6d34745e06b558b224ad8e84ab832b5c1928358610fe41e7f23` |
| `sft-math-nemotron-math-v2` | `u000.part0074.jsonl` | 300,047,967 | `af3528196e21192c90b059bce76ffd79beaf30c27e786dd011970e3401238dec` |
| `sft-math-nemotron-math-v2` | `u001.part0073.jsonl` | 300,015,541 | `003eddbfa8d92a1072c22f7e122100e628a84c48b12e0dd6957e30f37c73e9d4` |
| `sft-math-nemotron-math-v2` | `u002.part0074.jsonl` | 300,006,132 | `00e5f20b3e1f6c3d6b1d78fc0fa11c94baf93ffb1823347ebd356c73b6e88294` |
| `sft-math-nemotron-math-v2` | `u000.part0075.jsonl` | 300,040,652 | `4a3710b839f1558533e662b88bbf5aa65aa66b4da1cae81b5c6031ca539fa9ac` |
| `sft-math-nemotron-math-v2` | `u004.part0067.jsonl` | 300,002,003 | `b48aeebce53af4c3403c46410fc94f617686e26cd0e45f2e509983705fadfbb9` |
| `sft-math-nemotron-math-v2` | `u001.part0074.jsonl` | 300,026,952 | `e17c62a557a97d0d2d4e6c618f31eb216e33bc074f01669f16f5d5b5ec59886e` |
| `sft-math-nemotron-math-v2` | `u002.part0075.jsonl` | 300,007,444 | `64d76788346c766b206f71c777ff248bbfb50d05fb2aa5f3bfb53868cc19af58` |
| `sft-math-nemotron-math-v2` | `u000.part0076.jsonl` | 300,030,107 | `9ab0e2853646d762613140136e034957adf66e85d543b3b678037e2878a6f674` |
| `sft-math-nemotron-math-v2` | `u004.part0068.jsonl` | 300,023,788 | `2ef67c719ecee3a4a50625c031c8008f29c5b6e379a3c19403b521af499af36a` |
| `sft-math-nemotron-math-v2` | `u001.part0075.jsonl` | 300,131,229 | `2aa4c9a6a0e6dfff487e6cb25aa2744902dfad3e41b7029b4d53ab47c1dcb50f` |
| `sft-math-nemotron-math-v2` | `u002.part0076.jsonl` | 300,010,545 | `480b28fabc6a22898b7e63dc47f7185440f105053c684a4a45bc0467c50dbc8f` |
| `sft-math-nemotron-math-v2` | `u000.part0077.jsonl` | 300,015,558 | `405e3adb7625110e7ea8dd99cdab53f14b49bb705b5d74f5b344b5b790143f4c` |
| `sft-math-nemotron-math-v2` | `u001.part0076.jsonl` | 300,005,505 | `9a8b2ff7d6f9d3f9367c85b44fce47084372266946dd9faef9db585d5a804134` |
| `sft-math-nemotron-math-v2` | `u004.part0069.jsonl` | 300,000,869 | `f1fb478ddfc795d340da174aa3ddc1aca087dec804fe49c0762c4234f368e049` |
| `sft-math-nemotron-math-v2` | `u002.part0077.jsonl` | 300,008,789 | `f298274f187f707cd059f465b0b05f6c99750858cd2ef41d55b4eacdc2c51350` |
| `sft-math-nemotron-math-v2` | `u000.part0078.jsonl` | 300,008,349 | `b2dd12db2edd9344e78676035f79605a72582cc6c38390679443662559e9c0af` |
| `sft-math-nemotron-math-v2` | `u001.part0077.jsonl` | 300,005,931 | `9ddf703d7de22bdba0ad9a58b3a942767a6ea809d7505ace4559d3b068e1377d` |
| `sft-math-nemotron-math-v2` | `u002.part0078.jsonl` | 300,016,798 | `a38b7ba5781993acadef10aef71a3d0f71ef94472a2c7e0226653bd72fc6196f` |
| `sft-math-nemotron-math-v2` | `u004.part0070.jsonl` | 300,006,913 | `3f3db77d1342a0fc823d554a4f3673cc5d0993f8b90e8fad35e8a845743b2531` |
| `sft-math-nemotron-math-v2` | `u000.part0079.jsonl` | 300,090,319 | `27c79ebb1185913bf4b45f39956138e95dcbb48723ab7f65e0d585c0358a6b8b` |
| `sft-math-nemotron-math-v2` | `u001.part0078.jsonl` | 300,017,683 | `ceec9ce8e834e97965a09bde348b3a4f20b5bfab5140c1f814f9142eb0662596` |
| `sft-math-nemotron-math-v2` | `u002.part0079.jsonl` | 300,009,506 | `ee5938aced74c4215eab6ec10d116e37496ed220e59f4ce6a22a393775afc8bb` |
| `sft-math-nemotron-math-v2` | `u004.part0071.jsonl` | 300,001,456 | `2209f82ece8b3717604b225975898a545136a9d04efb8762b2ac98ceb7e86b77` |
| `sft-math-nemotron-math-v2` | `u000.part0080.jsonl` | 300,001,137 | `a9af633b77fe7c7dd56d917b248a1aac02300d5c7a75b1473d37b09fb09f3434` |
| `sft-math-nemotron-math-v2` | `u001.part0079.jsonl` | 300,004,687 | `ca4f15f60ee2b32a1e3c7cb279850c6ed466c5cfc7cb5e084b1a62189b1a87e3` |
| `sft-math-nemotron-math-v2` | `u002.part0080.jsonl` | 300,006,234 | `306b5b1fe8b7c53dc89e25326e7b4e87d06842cd7ef6fb709246d388c6daa5fe` |
| `sft-math-nemotron-math-v2` | `u000.part0081.jsonl` | 300,011,735 | `3b8b6d30465a9045019e1226552a961e2a9aa21a08a417cb11e5f72839e05dab` |
| `sft-math-nemotron-math-v2` | `u004.part0072.jsonl` | 300,000,372 | `286157816f94cff3be9d5f000d328a8f3843780ed957354f003fb47721edbadd` |
| `sft-math-nemotron-math-v2` | `u001.part0080.jsonl` | 300,017,365 | `df0305b8690460f2e5fe8ba9930a5691f024f94248d77ff94ba633b9f1ab115e` |
| `sft-math-nemotron-math-v2` | `u002.part0081.jsonl` | 300,006,699 | `0aba67391ff4abe2ef14b57c208e5bebb291e7996305e64942cbfa1d08871043` |
| `sft-math-nemotron-math-v2` | `u000.part0082.jsonl` | 300,038,699 | `e4866c7d56ce3a557138979e9e674c0eda4217434235d88ddc586449ded1038f` |
| `sft-math-nemotron-math-v2` | `u004.part0073.jsonl` | 300,006,249 | `4551ec8bbccda74d95ab4e51a9b5caef86d6dbea084965eac73dc622bfdcb58e` |
| `sft-math-nemotron-math-v2` | `u001.part0081.jsonl` | 300,079,044 | `4f464d99fc3a5bbe51ffee10f781692df73d712a5a789b199dfc16a87b514c5f` |
| `sft-math-nemotron-math-v2` | `u002.part0082.jsonl` | 300,007,061 | `436817bd21fc37a515bdc71a32ef6b81ce3903d454c70425eb5b247b3b1c3f25` |
| `sft-math-nemotron-math-v2` | `u000.part0083.jsonl` | 300,016,979 | `38a83f921b885aaece43c76039f659acddb1643f4a450f1f3b219ef8dc6acf65` |
| `sft-math-nemotron-math-v2` | `u004.part0074.jsonl` | 300,001,047 | `7b681dee17878ba4cbd980482efc5095913e7ebb6aa51ca3915efd01109358e9` |
| `sft-math-nemotron-math-v2` | `u001.part0082.jsonl` | 300,057,130 | `04fb80a20f4c0f567f42eff39ac07156548141469a1fa34bc1f19a03a2a8f5fa` |
| `sft-math-nemotron-math-v2` | `u002.part0083.jsonl` | 300,024,290 | `f6f69997952a86348ee0be37f8bdc5c8874cdd436a620a47ae859a66632b749c` |
| `sft-math-nemotron-math-v2` | `u000.part0084.jsonl` | 300,005,585 | `275e3e792224053365b407b82b5e145e1217022e2ec69563efbf0f0db573e5c1` |
| `sft-math-nemotron-math-v2` | `u001.part0083.jsonl` | 300,147,330 | `f60bd3a64fac1e608121f7b9a212628258c135a6442a5e6405f46720f60fec0c` |
| `sft-math-nemotron-math-v2` | `u004.part0075.jsonl` | 300,008,086 | `97ee28cdeb70ad71c7b580dd3556ed5e644cc011c7048cd4b1e7e9880e1a230a` |
| `sft-math-nemotron-math-v2` | `u002.part0084.jsonl` | 300,026,328 | `25ce327f1eed03f140b850a6d51eb19e5f6bdef2be20f3cf9cd9639a7fe9dcf1` |
| `sft-math-nemotron-math-v2` | `u000.part0085.jsonl` | 300,009,117 | `d385ec49ee5d001ad63536e2ff31f65abfef581d750b93bef3c5d1c065cca2a6` |
| `sft-math-nemotron-math-v2` | `u001.part0084.jsonl` | 300,023,848 | `26be368408a9b42981c938acaa14e694c2cc71334f73fa3fa0bec62dfc677c8a` |
| `sft-math-nemotron-math-v2` | `u002.part0085.jsonl` | 300,007,473 | `8491ee1e40bc74b4c65a50369e930fc74305349c1bf7837c218b4e5b19e543f0` |
| `sft-math-nemotron-math-v2` | `u004.part0076.jsonl` | 300,006,647 | `e8ebdb4b6b1408bfa1118c5024d79a3215b50be987b3924740057b543b7ff8f6` |
| `sft-math-nemotron-math-v2` | `u000.part0086.jsonl` | 300,033,859 | `b3ada9056fc9e1a208214c8ba66b05f9f1b5967399ee1d09b4db4a8df332f43e` |
| `sft-math-nemotron-math-v2` | `u001.part0085.jsonl` | 300,010,210 | `dde2227088f7b8ce29e9258f16985b98b1db4202f70692d0f51261d017773b1d` |
| `sft-math-nemotron-math-v2` | `u002.part0086.jsonl` | 300,031,545 | `7236a08f868fa66088b802f916a34026cc1e5d00d98ee3408211cc4594f2817a` |
| `sft-math-nemotron-math-v2` | `u004.part0077.jsonl` | 300,009,880 | `26eda49154cc21dc24bcfef06d8e0dc78856d23e1dc11abf346bd6c7f26ae6e1` |
| `sft-math-nemotron-math-v2` | `u000.part0087.jsonl` | 300,121,652 | `e1daa0f3e2b7d2023b227572842518d332cd92089613f969a272b32331cf650b` |
| `sft-math-nemotron-math-v2` | `u001.part0086.jsonl` | 300,004,322 | `d92cc6d2d30fb910a0029a91f7d386a338675084b445bc45132c66aa1c0693d4` |
| `sft-math-nemotron-math-v2` | `u002.part0087.jsonl` | 300,014,208 | `18a3ef8e894f4aa7058c6b329797b206e0a013169a3c8c875f6c45ca07e7f92e` |
| `sft-math-nemotron-math-v2` | `u000.part0088.jsonl` | 300,075,788 | `2759fe842bf21afd0db69b038e9ef6d9d9b057540f83eb499657a3362faf3312` |
| `sft-math-nemotron-math-v2` | `u004.part0078.jsonl` | 300,001,277 | `af3a358445693b82ee4606393951e40f7ca47273e4ec0b13b45f9db9cc9ca78f` |
| `sft-math-nemotron-math-v2` | `u001.part0087.jsonl` | 300,032,415 | `d7544b73762d85b7e4cf0e75e5581cc4ccb2cc5dc1e50d7a0aa133e203f81387` |
| `sft-math-nemotron-math-v2` | `u002.part0088.jsonl` | 300,005,709 | `dcf11c64c1dd26befa475d99f31e8e93e7a47bc6c25bb03fb5648c26f59a9566` |
| `sft-math-nemotron-math-v2` | `u000.part0089.jsonl` | 300,163,939 | `b2c32c29a8833bc6b3c7ad2beaec6e3040890dd5c1b7e9cd85d637d2a84998f6` |
| `sft-math-nemotron-math-v2` | `u001.part0088.jsonl` | 300,006,142 | `8c3db5423ac73e2c651f93abc8b13386b4fbb046b103f17a93df8384012e8f60` |
| `sft-math-nemotron-math-v2` | `u004.part0079.jsonl` | 300,018,824 | `9f3d8c2b3ea58704c30d166ad7c3c819653baf863f031952a2c8404c0508a1f6` |
| `sft-math-nemotron-math-v2` | `u002.part0089.jsonl` | 300,022,089 | `d076e984d7c2a0ac2e088ec04578df6cb2e5b147182e710916a863ead5d58db6` |
| `sft-math-nemotron-math-v2` | `u000.part0090.jsonl` | 300,010,431 | `302bfbda1420204fd739e55e213cac0d2d8d724e9a0d8656b215e69d4c96d8c6` |
| `sft-math-nemotron-math-v2` | `u001.part0089.jsonl` | 300,018,034 | `d20e5b9e0f014a9ca5673122fd03bdab3234b405bcf3aacdbf2149b9d2c86c3e` |
| `sft-math-nemotron-math-v2` | `u002.part0090.jsonl` | 300,034,761 | `0faf21584632b087e686cdddccbfa48f35348f836b0ccefc3b54c13c645788c5` |
| `sft-math-nemotron-math-v2` | `u004.part0080.jsonl` | 300,009,220 | `944021bb9fc8f573f117c87bb5974703335e20d23287f50a722fde8c64c3b8cb` |
| `sft-math-nemotron-math-v2` | `u000.part0091.jsonl` | 300,025,378 | `2d40f900e941c50e4519e86ced08daee93c36eb8e20d7f0754009be70258c579` |
| `sft-math-nemotron-math-v2` | `u001.part0090.jsonl` | 300,006,227 | `892a4d88e4bbf80e2490d292fced8a9bd115e90428812cc0213d13bd1b47d684` |
| `sft-math-nemotron-math-v2` | `u002.part0091.jsonl` | 300,040,784 | `90d87fbb35a617d4db06b3939078e79228db3a4b30941824ec9382b4b6fcfddd` |
| `sft-math-nemotron-math-v2` | `u004.part0081.jsonl` | 300,005,453 | `72eacba3a7bd5e5ab3f054618c206f38ba8e2afd0a1d2caf8cfbb39403b82105` |
| `sft-math-nemotron-math-v2` | `u000.part0092.jsonl` | 300,007,411 | `e8f397c1fd55baa55a32dde6880a5229517bf3499529f5d13db1a657cf5d0336` |
| `sft-math-nemotron-math-v2` | `u001.part0091.jsonl` | 300,006,752 | `5e853af022796df76a997735ea16087789bbca010035ca711899a9b3b0c4ee2a` |
| `sft-math-nemotron-math-v2` | `u002.part0092.jsonl` | 300,092,934 | `b188ae03a4712d31bd45fbd3c1df46917f06695e1e36c8b0bba295a08000c551` |
| `sft-math-nemotron-math-v2` | `u004.part0082.jsonl` | 300,005,104 | `58adacc418641f2976390d172bf4787ed5e5b95c609b03d20dab422a1fc4a99e` |
| `sft-math-nemotron-math-v2` | `u000.part0093.jsonl` | 300,156,178 | `83df8b19def90fa87c4674949b838f9b683bebda4bab025cf5ee49fc2949f29f` |
| `sft-math-nemotron-math-v2` | `u001.part0092.jsonl` | 300,003,107 | `105f07930825854ce937030c4cb8993d624e966aacc19f97caac16fa8870ead6` |
| `sft-math-nemotron-math-v2` | `u002.part0093.jsonl` | 300,020,760 | `bd1f6615335e1b560a15282c57eb579383bd8eb33e00a4e255992dcb3097bdf8` |
| `sft-math-nemotron-math-v2` | `u000.part0094.jsonl` | 300,015,279 | `b9d84b6ea90d5fb7d073e10beb9839b6ff25300ccceab73818813a89c972b577` |
| `sft-math-nemotron-math-v2` | `u001.part0093.jsonl` | 300,002,678 | `db801bea4e1befc2a85385e24928700b52100720230c1387cadbb635a5b6baa8` |
| `sft-math-nemotron-math-v2` | `u004.part0083.jsonl` | 300,004,154 | `c282a37a82de9ef98c1f96e589e50b34790daee69719cc707026b86028d0ce6d` |
| `sft-math-nemotron-math-v2` | `u002.part0094.jsonl` | 300,000,496 | `bd5082394c2cec83179c3c4c824c14a4a2733be329adef5d98391f637e0570a4` |
| `sft-math-nemotron-math-v2` | `u000.part0095.jsonl` | 300,170,892 | `2203fb51109ab62b14884fd0be77f4010552e674bae39b37827be6ecfece3527` |
| `sft-math-nemotron-math-v2` | `u001.part0094.jsonl` | 300,018,208 | `4990a0fb5c7cc11a929935f9edaae30943e6a5e0e1fa4eb73ad4982006a07fc6` |
| `sft-math-nemotron-math-v2` | `u004.part0084.jsonl` | 300,003,118 | `21af37ec7ab5f10e80f69ac17c1e17a3d2fa5889ca029786bb2d700b40ed44a0` |
| `sft-math-nemotron-math-v2` | `u002.part0095.jsonl` | 300,008,882 | `22b4fc64caafbd6cb7af2d542ca3f6d056f959cb4e70eefa2828cc16d0acaa1f` |
| `sft-math-nemotron-math-v2` | `u000.part0096.jsonl` | 300,043,653 | `d70032b85ccab4391ff0e489f2610c3208aa66503ee69bec6511955288b1a4b0` |
| `sft-math-nemotron-math-v2` | `u001.part0095.jsonl` | 300,014,716 | `7a2fa43112e65da515cf26c8a0378a17d03fdbbd44e69aa5d668c65d0aa72ddd` |
| `sft-math-nemotron-math-v2` | `u002.part0096.jsonl` | 300,012,541 | `1ebafe57e0763e82069b69f730d77f92f0b551ec166e3b2663509c03638d638d` |
| `sft-math-nemotron-math-v2` | `u004.part0085.jsonl` | 300,002,119 | `2d2127c0bb16dd92042ed61b838a3221d4e03d6f32df4bf74a97630212edda88` |
| `sft-math-nemotron-math-v2` | `u001.part0096.jsonl` | 300,032,156 | `c99622147a91aac7690605514deecc1750406b836664df95973a894f8ce41a7d` |
| `sft-math-nemotron-math-v2` | `u000.part0097.jsonl` | 300,019,306 | `e313dcc6e30dde80dd96e3f105207900802aa3f5a22156817b940965c167f23a` |
| `sft-math-nemotron-math-v2` | `u002.part0097.jsonl` | 300,136,194 | `01e89ffeef0e44868d71a10edc29cc81ea7f8df49df56d219fda9b1ed5e31b78` |
| `sft-math-nemotron-math-v2` | `u004.part0086.jsonl` | 300,003,257 | `779b436ad40002fc018c6453e41a6074c62348d460211ba9d520d0715abc9605` |
| `sft-math-nemotron-math-v2` | `u000.part0098.jsonl` | 300,009,190 | `67c478df9d8c4fd6f05b4be656339af455ab9945165bb8942f1daf8059b3b485` |
| `sft-math-nemotron-math-v2` | `u001.part0097.jsonl` | 300,021,706 | `82063a8448ce5fdd24f469d687ac607c716b9530bde946ded377d9266673f0ac` |
| `sft-math-nemotron-math-v2` | `u002.part0098.jsonl` | 300,002,319 | `de5fe1dee7f95adb491b9a31faf437d7405f1de478216e2497eb7bcf8ecf3c00` |
| `sft-math-nemotron-math-v2` | `u004.part0087.jsonl` | 300,004,107 | `4339e2d0aa4c9f11f8e83a3a0cae8e88d990db2b238b0ac8c57e85d70c30a9f7` |
| `sft-math-nemotron-math-v2` | `u000.part0099.jsonl` | 300,007,797 | `36d68f482cee670e98c658d110da45974685a79b4962b490340d804bc74ac8d5` |
| `sft-math-nemotron-math-v2` | `u001.part0098.jsonl` | 300,025,843 | `526348c7addf086694a6f6b48d1709a24a665e001ea198bcf89d11afbdf74eca` |
| `sft-math-nemotron-math-v2` | `u002.part0099.jsonl` | 300,056,909 | `f50e122f1023373919e31d0752ae7cd9d22e0e4d191e57f76ff27cffac04529f` |
| `sft-math-nemotron-math-v2` | `u000.part0100.jsonl` | 300,027,229 | `395b15e90236f4e10c66c1c588d568d87276982b3219d2df0aa55363d104a8a0` |
| `sft-math-nemotron-math-v2` | `u001.part0099.jsonl` | 300,013,218 | `12a9bafe3239740d4fda0a00bcf9fe451d94d41f096131b0724db0b7e835a036` |
| `sft-math-nemotron-math-v2` | `u004.part0088.jsonl` | 300,010,311 | `8a1aeca10bf02373028d98fc3c59251179776adcb3a893fd1a45fb0ab8dfa9cd` |
| `sft-math-nemotron-math-v2` | `u002.part0100.jsonl` | 300,001,017 | `80cabe1b4ed53bf3f5f6291baeb54b8f49d364db8ca44353af07505c2d33375d` |
| `sft-math-nemotron-math-v2` | `u004.part0089.jsonl` | 98,086,861 | `5fe1705b6317d4f7a68e8ac4a49084fa12e1f8fd5595f19017677982362bb977` |
| `sft-math-nemotron-math-v2` | `u000.part0101.jsonl` | 300,037,517 | `f3c89682965086172f0f4f32de1755eb92f1a410a8697c802c873affe63bdf96` |
| `sft-math-nemotron-math-v2` | `u001.part0100.jsonl` | 300,092,188 | `dfb45d9b827197ac38d5d7f9eaef4b8a4fdc13a65884cddf038086ce4bfc10b4` |
| `sft-math-nemotron-math-v2` | `u002.part0101.jsonl` | 300,065,021 | `35f207815f36d911294e1185d652a8546e1a16ec670d3219dc4758546b070893` |
| `sft-math-nemotron-math-v2` | `u000.part0102.jsonl` | 300,005,341 | `9e834375f4fa28e0259bb7fd8123677bd8cac467f844919470014dbdbf1ad612` |
| `sft-math-nemotron-math-v2` | `u001.part0101.jsonl` | 300,003,031 | `ad3f8d2dc741913e96cfecda6e74564706e550b8439b8c41af67d2da2ec35854` |
| `sft-math-nemotron-math-v2` | `u002.part0102.jsonl` | 300,033,926 | `d5caac553193a5582a598624ca7a3a68ae120df13f4530d7a80fe4304ca1b246` |
| `sft-math-nemotron-math-v2` | `u000.part0103.jsonl` | 300,025,181 | `e9451364e9d34f6e076d22a6ca4e95d56a4f1f962ae4de7521eb858f1aa24a87` |
| `sft-math-nemotron-math-v2` | `u001.part0102.jsonl` | 300,025,083 | `15d6eb354eba1b972b2841c14635a00909648d06150c58298e0982f4a4856e7f` |
| `sft-math-nemotron-math-v2` | `u002.part0103.jsonl` | 300,043,142 | `a0109f310e85c1874c5f8c5fa905981fb72c2b5e4bbf9b5d9da55d998e92e750` |
| `sft-math-nemotron-math-v2` | `u001.part0103.jsonl` | 300,003,721 | `60cb0d878044c2e7dfbac8fdf98b8c075bde1df81c5c5317203e06c07a5546c8` |
| `sft-math-nemotron-math-v2` | `u000.part0104.jsonl` | 300,041,768 | `e5d4909edd4f8fe417f3feb86eecee23dca5d5a76c04995058befb7ebf983d61` |
| `sft-math-nemotron-math-v2` | `u002.part0104.jsonl` | 300,019,806 | `214a736712268593f88a11d0248ace2328ad738480a6c4f67af1ca3305991288` |
| `sft-math-nemotron-math-v2` | `u001.part0104.jsonl` | 300,028,525 | `555cb6baf88b736ba0a7bff8700565585e3596db00e0c14002e0e02a7bd159fb` |
| `sft-math-nemotron-math-v2` | `u000.part0105.jsonl` | 300,004,771 | `3359a644469f3c82ce8d376c5fe3ef422df139ac3e3a765884854f4b019e26a5` |
| `sft-math-nemotron-math-v2` | `u002.part0105.jsonl` | 300,002,878 | `6e6fbfc8b998cee61e8ad59e504253ccfded401828ca3dd9e9db625935fbc766` |
| `sft-math-nemotron-math-v2` | `u000.part0106.jsonl` | 300,022,303 | `ff0d1a2c09323ebf6f355203b4fd3172cca485459fa33ad706f3bad81785b946` |
| `sft-math-nemotron-math-v2` | `u001.part0105.jsonl` | 300,025,746 | `7be7a4665827bee77af44598190d0a4d61032cc036044d98dac4d63b655b2d56` |
| `sft-math-nemotron-math-v2` | `u002.part0106.jsonl` | 300,030,777 | `955d5224e02f160cb37c38ad5101e35e3c47119b621144b1c78d14558ebf7005` |
| `sft-math-nemotron-math-v2` | `u000.part0107.jsonl` | 300,002,996 | `053c9df30cb1f6c63d084255741c162f5988b5ec0a9c9cbe77ac5ebab58111c7` |
| `sft-math-nemotron-math-v2` | `u001.part0106.jsonl` | 300,010,888 | `4fb2a386cdd185c5c79dd70612c4268470459c7849dcb629ed4122050ecbce72` |
| `sft-math-nemotron-math-v2` | `u002.part0107.jsonl` | 300,009,536 | `02b17ebd756383d4f18a51cd632e9bdcd1e4760797899c8fc9867e5bb65761b9` |
| `sft-math-nemotron-math-v2` | `u001.part0107.jsonl` | 300,005,311 | `fd8abf6c2704440f6bce891b4aebe336b119b1f1b9594dbe247920ab518fe800` |
| `sft-math-nemotron-math-v2` | `u000.part0108.jsonl` | 300,036,111 | `c3ac1015fa3be4deb09fe64a0fe60451c663d6d2205c910e441b408339d33275` |
| `sft-math-nemotron-math-v2` | `u002.part0108.jsonl` | 300,014,060 | `7fcdc359fa2cb379beb7033a61f3e99d93864f5fc6d4c393863460f67af2550e` |
| `sft-math-nemotron-math-v2` | `u000.part0109.jsonl` | 300,077,046 | `3da2436357c113197da7191e58708b28b6ef55e16f199f830f7f631c1fbea2e4` |
| `sft-math-nemotron-math-v2` | `u001.part0108.jsonl` | 300,016,570 | `75c8d5c94537bfc4f23acbce9923f5f1a2e36422352d4b8010329dc626d44b05` |
| `sft-math-nemotron-math-v2` | `u002.part0109.jsonl` | 300,015,829 | `3239c7b07cd76faa31d6e7be50cd8ac09203116a9eb0669979f9c10be7093cce` |
| `sft-math-nemotron-math-v2` | `u000.part0110.jsonl` | 300,011,057 | `ebec0b6042233508a3da188a635e8e28bb2f986483cbace50c894d89cbc429f3` |
| `sft-math-nemotron-math-v2` | `u001.part0109.jsonl` | 300,004,804 | `5876fe0fb07225e5e25f01f614b9fa7280ad220018080a98910432e943ad0198` |
| `sft-math-nemotron-math-v2` | `u002.part0110.jsonl` | 300,067,728 | `e9fd9eed00942d1403774235f322176a70ac9c6442cafe923d3e1dbca0e1ef16` |
| `sft-math-nemotron-math-v2` | `u000.part0111.jsonl` | 300,051,773 | `3e01956855955c76c4016ce4bdc05f433e2ccc4d207ba1f809c7900065645efa` |
| `sft-math-nemotron-math-v2` | `u001.part0110.jsonl` | 300,010,602 | `6a8cc63283115799ceb97cd1d41eaf7596949f110f39b3ec9ae53c2e5f3b714d` |
| `sft-math-nemotron-math-v2` | `u002.part0111.jsonl` | 300,014,919 | `f77b4169d9d53b380f299b007303d8dc8570facf4665a3cc60324a76e38c92e2` |
| `sft-math-nemotron-math-v2` | `u000.part0112.jsonl` | 300,000,589 | `aab64f936dc9d5b21ceeceeb4ba318638f92747efcd7e96738bd27bad31750fc` |
| `sft-math-nemotron-math-v2` | `u001.part0111.jsonl` | 300,011,036 | `b5588a2ee25ea77c357f2c8d810b73704271101ef999c157ad288696c47f2d31` |
| `sft-math-nemotron-math-v2` | `u002.part0112.jsonl` | 300,062,728 | `284ed508f0cb0703f791bd2533d50661e3db882f160fbd23fd46b416513e94ad` |
| `sft-math-nemotron-math-v2` | `u000.part0113.jsonl` | 300,016,968 | `7a9abe8bfb115a786b5dab280821e8b774450bb9cbcebe59ab299395a87b212f` |
| `sft-math-nemotron-math-v2` | `u001.part0112.jsonl` | 300,003,850 | `26fed491998059f19ac4a0ec6bcf374ee35ca97fdffa7c86faa2b5397c038367` |
| `sft-math-nemotron-math-v2` | `u002.part0113.jsonl` | 300,005,214 | `7e8ac841031321c2adc17902bf9ed4096ac61c7019611efba8e4ba1517675ed0` |
| `sft-math-nemotron-math-v2` | `u000.part0114.jsonl` | 300,063,639 | `e18c7891143d1e0c1b6150a9b65063dbe71b9db43760e1fcfbedb21d32e69312` |
| `sft-math-nemotron-math-v2` | `u001.part0113.jsonl` | 300,017,531 | `29358fa930601f01a08a3ec6e7b459811b1d5ad77cf45d390ffc0c280ffeb704` |
| `sft-math-nemotron-math-v2` | `u002.part0114.jsonl` | 300,094,858 | `99185341951f777cab6c7941b8bc0cabe15d909a09d64001fefb0a5f69d3e57d` |
| `sft-math-nemotron-math-v2` | `u000.part0115.jsonl` | 300,004,037 | `7a4c95e1f816b39f6f0d1e177baaaa6427de104c6cc86eff8f4fb43230b815d1` |
| `sft-math-nemotron-math-v2` | `u001.part0114.jsonl` | 300,014,190 | `c43e27f9d819d965bfe9d180dc8c0b6bbfd3a142685f6b2f9f6b918d7caf5df5` |
| `sft-math-nemotron-math-v2` | `u002.part0115.jsonl` | 300,041,451 | `06250494e3b95fe853666fdc614bb9eab204061c9754686ed8e409523873824d` |
| `sft-math-nemotron-math-v2` | `u000.part0116.jsonl` | 300,119,485 | `529ebdd98063619c0089dd2c9dd5fc76ac3a6bbfd6ea28bca18e169699027f5c` |
| `sft-math-nemotron-math-v2` | `u001.part0115.jsonl` | 300,017,479 | `a2995e40ccf1d2e4f1b51fe8a692f4b558d78b4456a05b336d62418fa78a87b0` |
| `sft-math-nemotron-math-v2` | `u002.part0116.jsonl` | 300,006,731 | `2cb23d97abcf1835988a5926e9abd706d3dfa23dd3d91aa28cd40a73e0ac1703` |
| `sft-math-nemotron-math-v2` | `u001.part0116.jsonl` | 300,034,698 | `dd8ff934e3ab9eba6d4c7d1257ac8dc401c518383e29ccc47e873e634e6fe9f5` |
| `sft-math-nemotron-math-v2` | `u000.part0117.jsonl` | 300,017,879 | `8eee7a86c0dbd008b6fe386ad2afcfb086b2fe4b4ff3d898e2bb7f7787349952` |
| `sft-math-nemotron-math-v2` | `u002.part0117.jsonl` | 300,059,542 | `4e22753052f4283a5c52c39edc4127061b54ae0bd6d46433d167b7264b0d2f6f` |
| `sft-math-nemotron-math-v2` | `u001.part0117.jsonl` | 300,006,208 | `12956e53f2602ceaef150f8583b8b46440773fc65c69a904ac10ecd2f28efba8` |
| `sft-math-nemotron-math-v2` | `u000.part0118.jsonl` | 300,019,337 | `f8d48c354c37a0ab316650b0474de60a04098602a71579163b23ea6cdb192e6e` |
| `sft-math-nemotron-math-v2` | `u002.part0118.jsonl` | 300,001,894 | `959182ca1785b019189a4d6a951ae9b4a3602fb873b1036021febfaf1ab23a3e` |
| `sft-math-nemotron-math-v2` | `u001.part0118.jsonl` | 300,003,539 | `4106242449be6171a169a3de94233e117e8856df8f5efd44731d9deac76b823e` |
| `sft-math-nemotron-math-v2` | `u000.part0119.jsonl` | 300,009,887 | `8726b1f75223a664de9292bcf22be3dff82e3fa385641bcd4f037a74200a4566` |
| `sft-math-nemotron-math-v2` | `u002.part0119.jsonl` | 300,039,317 | `f3128eedaac072bb117d14d33125f067667c4965af9b9970cbda1c88b237b63b` |
| `sft-math-nemotron-math-v2` | `u000.part0120.jsonl` | 121,581,426 | `d6faf74a7bcac9458e37a4cd8ff645809187ed185c577d9e9501e88d14093908` |
| `sft-math-nemotron-math-v2` | `u002.part0120.jsonl` | 117,223,766 | `7840a1e478938d1d5d9903947d1a9b014a99d41ace4fff0b115301745e2dded2` |
| `sft-math-nemotron-math-v2` | `u001.part0119.jsonl` | 300,083,416 | `613a28ffda52ce8f5fe2a6218d15741a158ba36f3efe0841d6d78c57b498301a` |
| `sft-math-nemotron-math-v2` | `u001.part0120.jsonl` | 127,337,285 | `4836a879dfb38d91650ab03f33c1a084913f5112ac71406e719939b83b81a337` |
| `sft-math-nemotron-proofs` | `u000.part0000.jsonl` | 300,005,219 | `dd82a8577038899c92d3405a4484730f70501a048a8e6570d4037b621eb4c153` |
| `sft-math-nemotron-proofs` | `u000.part0001.jsonl` | 300,009,979 | `d6e8ba94c6145adce57e621ded58e98cb07b5f539780f88c44753c67aa944b63` |
| `sft-math-nemotron-proofs` | `u000.part0002.jsonl` | 300,009,946 | `203fad8a8b543c38b4d364830b7ad0f3c1c52ebedd79703aac3fea79aed7dd52` |
| `sft-math-nemotron-proofs` | `u000.part0003.jsonl` | 300,010,549 | `0b96e07a8cf0cfe12fac6ee8cde4997d5d4e5140937f0e61fad6478449131282` |
| `sft-math-nemotron-proofs` | `u000.part0004.jsonl` | 300,120,836 | `5277139219bba84919c6d7266f47988b70968239f0c7852d581e98e0e61f6dad` |
| `sft-math-nemotron-proofs` | `u000.part0005.jsonl` | 300,012,963 | `618356941cd0d4ae24d5945b88392e269e22db75c3d0c5383fb35b44153a9f95` |
| `sft-math-nemotron-proofs` | `u000.part0006.jsonl` | 300,017,057 | `89d1504d95ad6c3f51a2127057e1ea4d3b912485854ca3302cd53d5a2e5270da` |
| `sft-math-nemotron-proofs` | `u000.part0007.jsonl` | 300,003,530 | `1ada410872c6a056f1d51f46a048e25957ebab681bea7136b0a0de25cdb65384` |
| `sft-math-nemotron-proofs` | `u000.part0008.jsonl` | 300,011,715 | `fdd329d10a53c3c06b4caef0cf8474232ffdbea60c34be261e288d5d22203e2f` |
| `sft-math-nemotron-proofs` | `u000.part0009.jsonl` | 300,002,554 | `f9473e435626fe5e4186f294203797f17c01efb2da0a560696e9f2907c0d2113` |
| `sft-math-nemotron-proofs` | `u000.part0010.jsonl` | 300,000,600 | `10e9a7ca34a9916739edc570385841f4cd28b0746ce686e66b22662aeb339ceb` |
| `sft-math-nemotron-proofs` | `u000.part0011.jsonl` | 300,036,178 | `d5998ce8ea906f5b4750afb69b557929a33f658cc13791cc967d175a4afae134` |
| `sft-math-nemotron-proofs` | `u000.part0012.jsonl` | 300,022,010 | `3c6198e2e635326a33175e3553820c4dcb6df75db6df6a4a578582c41aeff136` |
| `sft-math-nemotron-proofs` | `u000.part0013.jsonl` | 300,002,545 | `4abb1418c1d777d31bb4809371b9e307d547644836a9444aa8b077fb21efcb2f` |
| `sft-math-nemotron-proofs` | `u000.part0014.jsonl` | 300,016,112 | `b2b3128169626bf9c0bb4de7af87da95b4a471d75cf3182a375ffb7f106075f6` |
| `sft-math-nemotron-proofs` | `u000.part0015.jsonl` | 300,012,144 | `786e607c1be36f26385fa0a350e475ece509a8b379f795cb1fd6f1e3b85190b9` |
| `sft-math-nemotron-proofs` | `u000.part0016.jsonl` | 300,040,996 | `54a72a3921bd3125f08c0ec2a26d14ec891f5eeec3c19cb83a3b5b6c29ca67da` |
| `sft-math-nemotron-proofs` | `u000.part0017.jsonl` | 300,063,049 | `8896b14493d107c6342402ea3057ca1c6ccd1c28aa84834b0f60fc7d822c1fe7` |
| `sft-math-nemotron-proofs` | `u000.part0018.jsonl` | 300,012,886 | `de1546e37bf11d9e8330b1676544cffc6c33e0940237611d03409fc843ae921a` |
| `sft-math-nemotron-proofs` | `u000.part0019.jsonl` | 300,018,328 | `0830a0c5bc5ffc9bd780c9a0afd9af960325d7b9becb3cd2b5d87360c7d8a2bd` |
| `sft-math-nemotron-proofs` | `u000.part0020.jsonl` | 300,001,376 | `f2420fba75233d6e153344f2bdec3613f1a01892474e5a31c72a9768a6c94880` |
| `sft-math-nemotron-proofs` | `u000.part0021.jsonl` | 300,001,766 | `6532a476172993b5a75fa4924561a3873a0d6fd481ee003bd778a88c9940d369` |
| `sft-math-nemotron-proofs` | `u000.part0022.jsonl` | 300,010,669 | `6261c3650365f8134dd1bc5bd2e2d17d193512180b48f569ca39036500688058` |
| `sft-math-nemotron-proofs` | `u000.part0023.jsonl` | 300,044,398 | `c90823152008e21e8fa1c2e48430b0339f95865d68d358c60f14cdb916cb308b` |
| `sft-math-nemotron-proofs` | `u000.part0024.jsonl` | 300,041,129 | `b03cd8e99877cd30a3827835d3b801d6c349f6425759b07da4deb1fb4d85342f` |
| `sft-math-nemotron-proofs` | `u000.part0025.jsonl` | 300,020,936 | `e6a282d6e9d8d28ddbe86be481d19bc5e73b204c399506e4ac21b3d611266e42` |
| `sft-math-nemotron-proofs` | `u000.part0026.jsonl` | 300,055,880 | `82d7255a7103e2d139492b6f6a575f863f3b145834aabdcab48290631b815198` |
| `sft-math-nemotron-proofs` | `u000.part0027.jsonl` | 300,024,733 | `b1288eb1d73661f0cb8dcfd7feb6dab0e815f071f6d557d7be10717b57a55ab8` |
| `sft-math-nemotron-proofs` | `u000.part0028.jsonl` | 300,020,780 | `47030ad4894ae4e4015708cc41dafe89e1f3c1e87feb0397f47852758fe05b60` |
| `sft-math-nemotron-proofs` | `u000.part0029.jsonl` | 300,014,348 | `8dd91e78222f285d6b747ce4d3ac195f0f2483ef9c9565bdbafd204a805a7fff` |
| `sft-math-nemotron-proofs` | `u000.part0030.jsonl` | 300,024,010 | `38ba5fee96f9b54347c4a0ea64a6a9e9b6be7a9e3327a70b978d7c2b07c7bf7d` |
| `sft-math-nemotron-proofs` | `u000.part0031.jsonl` | 300,027,580 | `e72895ef27183fc16bc053474e0088ef4b76ce370c4cff6f8043db54670b498c` |
| `sft-math-nemotron-proofs` | `u000.part0032.jsonl` | 300,018,732 | `a39900896bd2b7397f46d6abb8fcd146d2128a5c221f2722f3b7f9e6eb235dfd` |
| `sft-math-nemotron-proofs` | `u000.part0033.jsonl` | 300,009,344 | `168b8757cd02adeaefc4f567e2505031ba028f3352bc33d1390b902e0a21082b` |
| `sft-math-nemotron-proofs` | `u000.part0034.jsonl` | 300,030,400 | `0cc634baa66abcfe8eae20d1082d3136ffe685e116244d5d4c117d84d5798920` |
| `sft-math-nemotron-proofs` | `u000.part0035.jsonl` | 300,039,573 | `90c5c6575a293cacd2372de4b6c825f726b9048d6e78d525e200879b66a0de15` |
| `sft-math-nemotron-proofs` | `u000.part0036.jsonl` | 300,044,585 | `843163aaedc1ad09247942f2579cee34044fe66bea20d81038a6315a15a1085c` |
| `sft-math-nemotron-proofs` | `u000.part0037.jsonl` | 300,040,605 | `6baccb2df101c3b9447933cb902448ebcf7186fd0a14a95dfa83aa6692811445` |
| `sft-math-nemotron-proofs` | `u000.part0038.jsonl` | 300,028,145 | `dc1e9666720f4f93ff90fbce4e4210d68ca86471f7f64f5dcd6f21ec73f3b9bb` |
| `sft-math-nemotron-proofs` | `u000.part0039.jsonl` | 300,011,598 | `2a51cc6a748b90a8dd988bf3d1085700ccea7baba88a1163c7fb31b0177e1139` |
| `sft-math-nemotron-proofs` | `u000.part0040.jsonl` | 300,007,556 | `34c3450ad1f415cbda4d65abd71d7ddd1c535d6715afc9d43a166682ed470797` |
| `sft-math-nemotron-proofs` | `u000.part0041.jsonl` | 300,000,146 | `90d418b07b620d6c26aec305de65c12a5ec5ed58ac24ebb33eb7f233304e84aa` |
| `sft-math-nemotron-proofs` | `u000.part0042.jsonl` | 300,016,770 | `66bdf7a8416a00b7157e4dba145a6813ad904396dc42497c15caa82ff8eddd11` |
| `sft-math-nemotron-proofs` | `u000.part0043.jsonl` | 300,020,604 | `3f2e6c97005340c729c498b9a910f49ac0c9f909528d14390d5727985bb3372d` |
| `sft-math-nemotron-proofs` | `u000.part0044.jsonl` | 300,003,887 | `35a5c6ff036f136eebcc1f3aaee0efe3c45090e7d96b92d30740a5c04050bb95` |
| `sft-math-nemotron-proofs` | `u000.part0045.jsonl` | 300,013,341 | `bd05908b29ed55c42fd9a6b54dff812550a006f64c8249855dcbccfa23d4223c` |
| `sft-math-nemotron-proofs` | `u000.part0046.jsonl` | 300,072,765 | `8fd98c11a43e2bb3f28f4152c2165d1508723629d7e8c9b4d647777f348f884e` |
| `sft-math-nemotron-proofs` | `u000.part0047.jsonl` | 300,029,714 | `cafba32aec0b6bd781c63f11fb028fc740dcff887aef97429032d124867e65c6` |
| `sft-math-nemotron-proofs` | `u000.part0048.jsonl` | 300,000,280 | `4b69abd290e762a29f1b56c8c0b89f3930b285e303bd55073fa7d90281d95270` |
| `sft-math-nemotron-proofs` | `u000.part0049.jsonl` | 300,025,566 | `be90ba40ef0fd96bcb08a92f54a4e845098c10c2193f56787c0ed20b2e0cea83` |
| `sft-math-nemotron-proofs` | `u000.part0050.jsonl` | 300,005,312 | `c10656a2e7d28d5135effd8bb5113851a9379c37bcde73692681e2e66f6a9bb2` |
| `sft-math-nemotron-proofs` | `u000.part0051.jsonl` | 300,031,636 | `b1d4d713438139e7533e1c4eec975d52b90a49dabe5b3d5c0e633c20aeee20a1` |
| `sft-math-nemotron-proofs` | `u000.part0052.jsonl` | 300,014,132 | `72cc65a3c22b515551a71c4c019cff99baa53fe8cd60e79ff69e8a2e62d25884` |
| `sft-math-nemotron-proofs` | `u000.part0053.jsonl` | 300,002,027 | `10eeb56986d7bddada86a49f88171db088ad1dead51d118a4b74928ef46264c9` |
| `sft-math-nemotron-proofs` | `u000.part0054.jsonl` | 300,018,591 | `f6fe82170925e5299a019f7dbaf22fc8825895a983f4b2f2cb543ec244afcf66` |
| `sft-math-nemotron-proofs` | `u000.part0055.jsonl` | 300,012,059 | `2758ea73eec1832c30b66f406901a435249b507adddc3651d0bbe9beafeb6d01` |
| `sft-math-nemotron-proofs` | `u000.part0056.jsonl` | 300,044,175 | `ebe5667592be869153cd86d457e8dc2e70b214c14a5fbc1e0461a303460b0fa6` |
| `sft-math-nemotron-proofs` | `u000.part0057.jsonl` | 300,001,915 | `6766634e7776677aa10e43fa97b57c27b3b77e5e3bcd09f326117a0b7245bce2` |
| `sft-math-nemotron-proofs` | `u000.part0058.jsonl` | 300,024,031 | `ec6a8f42acac30e927dbdf7c6bc6c37b38315e0aa095098ad60a9688387fe564` |
| `sft-math-nemotron-proofs` | `u000.part0059.jsonl` | 300,008,984 | `fe257b57db7730f8c3777b2daf1a248db7e45adc2551c0616485d3753c60b527` |
| `sft-math-nemotron-proofs` | `u000.part0060.jsonl` | 300,023,851 | `1d5884763ff817a1af18b0b2a39ebd6b7b89fdd337105e988587dc2cf6b8bdde` |
| `sft-math-nemotron-proofs` | `u000.part0061.jsonl` | 300,060,921 | `db2c92ee6cec7e3002ec7ae93d8a24943cdd49007412eca147d9c7ba4e5e3fd9` |
| `sft-math-nemotron-proofs` | `u000.part0062.jsonl` | 300,021,454 | `81b2a850fdc5c058d512ace49ce688c1a1a658e9780fe7a6ca0a472b7dfed153` |
| `sft-math-nemotron-proofs` | `u000.part0063.jsonl` | 300,003,326 | `7d422174e279fb812afa980329d242ecb420efb5181354e9b2b804d6bdf8ab19` |
| `sft-math-nemotron-proofs` | `u000.part0064.jsonl` | 300,029,490 | `b77dfb3ccb5ed9f20e98665cb9e964fbe92ea2688bf17138725f3c5189e90c00` |
| `sft-math-nemotron-proofs` | `u000.part0065.jsonl` | 300,007,872 | `f6ac5a91dd8ad945ba9884f9d19ad2037277f51707aae8ff2feebad772e5e6a5` |
| `sft-math-nemotron-proofs` | `u000.part0066.jsonl` | 300,021,197 | `b4cef45b0dc98c81a7ee664df4aa06fd7d1cd75b5068e63bfd38d7552d397fc8` |
| `sft-math-nemotron-proofs` | `u000.part0067.jsonl` | 300,001,520 | `095e63af901e5c7ff75a8cb836d83307ec789a9d207433aff855af82361341b2` |
| `sft-math-nemotron-proofs` | `u000.part0068.jsonl` | 300,018,909 | `6a056e819c7207f2bc4f3aa459ac6255e8992c7b81b38690e7bcb05b7ef3f606` |
| `sft-math-nemotron-proofs` | `u000.part0069.jsonl` | 300,052,890 | `47be19e92f164647ad674304011e2752064937fc8631b98515984793dbbaf2b2` |
| `sft-math-nemotron-proofs` | `u000.part0070.jsonl` | 300,042,712 | `c8ffb28ebb7a840b850a9c57e4dfca88e2e0e914ac5eead82d735b0d5de7c3c3` |
| `sft-math-nemotron-proofs` | `u000.part0071.jsonl` | 300,007,645 | `bddb0af78573f67ae89ac5d0ee1a498a5a34d5834c1a48c42e7df987ab047454` |
| `sft-math-nemotron-proofs` | `u000.part0072.jsonl` | 300,100,009 | `51397a1e8337346ddaa41b0327dffffbb74f42b543e7783ab6a7409774098c0c` |
| `sft-math-nemotron-proofs` | `u000.part0073.jsonl` | 300,013,747 | `1532c85b4ccf4dcba2bfb2af008cf6d217a9ca64645caef7f260ec35b9348949` |
| `sft-math-nemotron-proofs` | `u000.part0074.jsonl` | 300,022,620 | `60cc1a95465a75440fa95b5ba0a0db03e64728ce0bc2b012616b123b5af878ff` |
| `sft-math-nemotron-proofs` | `u000.part0075.jsonl` | 300,004,591 | `fb9e5b1ace3b378e4935442205ce83c951bb3d5afd7c4df6dcd590a8c601124a` |
| `sft-math-nemotron-proofs` | `u000.part0076.jsonl` | 300,079,749 | `73ca4ec38b04a72b5aaabafb17dcd34b718054458143fee1cb9121a1dbb5e119` |
| `sft-math-nemotron-proofs` | `u000.part0077.jsonl` | 300,046,249 | `b795ed1adba930931cc17718028872648844b8fcab2ad3f887e9b07871e73b20` |
| `sft-math-nemotron-proofs` | `u000.part0078.jsonl` | 300,041,304 | `d364b7d85d0688ea790cd6c66d80c93c9e1050772e67679210a5a2890a68aa11` |
| `sft-math-nemotron-proofs` | `u000.part0079.jsonl` | 300,034,278 | `66243e53df46d9ba2fba4bb616ff87b525dedeb889b8741c191c51c44ad8376e` |
| `sft-math-nemotron-proofs` | `u000.part0080.jsonl` | 300,002,384 | `616b1740601edab2bbc4271258acba7fff7f453ddd7d2259824fa64318f60b27` |
| `sft-math-nemotron-proofs` | `u000.part0081.jsonl` | 300,007,129 | `c3b15745a87af14e93a6e7eb34343b42a60e595f662c29685ded731c50843b13` |
| `sft-math-nemotron-proofs` | `u000.part0082.jsonl` | 300,004,292 | `a9c77105a4ed183daf1ea065b920dc3227424f4f62119486c1e86eee92b5992e` |
| `sft-math-nemotron-proofs` | `u000.part0083.jsonl` | 300,009,362 | `31f0d03c1cf932fa24142c321c979f0a1125510735d0c9d013be41656d9f0365` |
| `sft-math-nemotron-proofs` | `u000.part0084.jsonl` | 300,064,517 | `289fcc991031718915f01f8dbbdeabf63ef7c862ec942438b7b92e7c522829ef` |
| `sft-math-nemotron-proofs` | `u000.part0085.jsonl` | 300,029,926 | `4bdf9769cde37dc4a6ec9d44f2bfaf51a7ab2e23159a09ef208ada21961ad3a2` |
| `sft-math-nemotron-proofs` | `u000.part0086.jsonl` | 300,017,398 | `1a129defd9261b37820e6f49a2fff430d798d7e8a34c3fd677f2a94345f35313` |
| `sft-math-nemotron-proofs` | `u000.part0087.jsonl` | 300,046,386 | `b58f7f5873810f2dd9b1e8656ab615a7b04d1f3b274d1daa002b902c28ec02f6` |
| `sft-math-nemotron-proofs` | `u000.part0088.jsonl` | 300,018,558 | `73ce1a44e81d2f9cab5ece74a9c7dc018c0fbeafb46e29b848fe86c7f2fa5a08` |
| `sft-math-nemotron-proofs` | `u000.part0089.jsonl` | 300,009,473 | `afb0f634cd812fd330f40fe4fadc56752904f89dcbb1f60f23011d902f6cae65` |
| `sft-math-nemotron-proofs` | `u000.part0090.jsonl` | 300,001,960 | `4d1ad49ee6c5fc3ba424e282c9099a359f7074cbd2cda0dc1da8b03462016266` |
| `sft-math-nemotron-proofs` | `u000.part0091.jsonl` | 300,012,627 | `f12dfb4582c1da92c19a9e3362b607128efddfd2d116a98797c470b416880177` |
| `sft-math-nemotron-proofs` | `u000.part0092.jsonl` | 300,035,878 | `76bdff3228b3ed1b9e75fbff1611fdb58a04e2e4bad9eeba1d869f8ff7e5c66f` |
| `sft-math-nemotron-proofs` | `u000.part0093.jsonl` | 300,034,553 | `5721cdbc1b6bf98a8c6a07b1301752d59d2a643a66efdb693049551614c9ba89` |
| `sft-math-nemotron-proofs` | `u000.part0094.jsonl` | 16,191,897 | `22d47379c3348ff3e693b4948a88125f26a2c998d4db72569b6958aa1940e05b` |
| `sft-math-nemotron-sft-math-v4` | `math-nemotron-sft-math-v4.jsonl` | 18,526,574,137 | `15cf1ff1cb0598540fc7d9f537400823ecdf3c2ee5a6572570989a8d59fff846` |
| `sft-math-openr1-math-raw` | `u000.part0000.jsonl` | 161,568,374 | `8e894ba334c09fe84918734bd0cf6fbfc87888d6f67a75b273c932e1a1db95f1` |
| `sft-math-openr1-math-raw` | `u037.part0000.jsonl` | 205,664,650 | `c7623087db9c93f158652524df9984ec0c04ef384a2aec769196b92c34abda0d` |
| `sft-math-openr1-math-raw` | `u014.part0000.jsonl` | 153,109,040 | `5142d9937a1e9b56c5a4ff6bd55ab9cfb31371e3fa39822aef7cc64e97227bf8` |
| `sft-math-openr1-math-raw` | `u004.part0000.jsonl` | 216,225,538 | `4eeb90bf2125abfeb8763c37bdd1e831c3be99bf4e72be5c0adfa7d515eeb3a5` |
| `sft-math-openr1-math-raw` | `u036.part0000.jsonl` | 173,315,941 | `5f9ae7b44668acaf5db7c2f6629e41a171f8f3da07ca853045acc06cdc74e3b6` |
| `sft-math-openr1-math-raw` | `u001.part0000.jsonl` | 191,071,566 | `8a700ec24c0f77b233dc147dcc546d1b6e7f56502800876df939057bcf3a2660` |
| `sft-math-openr1-math-raw` | `u015.part0000.jsonl` | 139,367,185 | `883270780f6d8ee8043d94d7ea541049907d1be1e2819bc14815f75b395e9be8` |
| `sft-math-openr1-math-raw` | `u010.part0000.jsonl` | 191,599,196 | `00fcda8fa32d14d3619497838b3adefd2eea0ae062f3bc0f04e7ee1fcf4e0baf` |
| `sft-math-openr1-math-raw` | `u007.part0000.jsonl` | 175,084,873 | `55e9afdb86329add1a26ad7ca883e106859573a6db017485d492f57eb6d439f1` |
| `sft-math-openr1-math-raw` | `u009.part0000.jsonl` | 176,360,843 | `48bbaa5f0d931b6ae28984ea2caed0686277cb7c0712565732eece8478ca0c20` |
| `sft-math-openr1-math-raw` | `u008.part0000.jsonl` | 175,007,047 | `fe0322d2758432fcbe8b35beb2c7715e81bf0ac866ad2d5d6afac5bc2ee561f0` |
| `sft-math-openr1-math-raw` | `u012.part0000.jsonl` | 169,167,879 | `54879ad511581f4742f57a2cf326d609646430e12ebfa0de9eaac13d77ac9687` |
| `sft-math-openr1-math-raw` | `u011.part0000.jsonl` | 181,672,218 | `918ee6690df8627ef25b2c1af3c1f9b489d8773161be1291a526b9012259997e` |
| `sft-math-openr1-math-raw` | `u006.part0000.jsonl` | 176,498,511 | `2c685fe8ffffd2254e6e42c864d6aab9184577ef0a0c4740f5045775e74eab17` |
| `sft-math-openr1-math-raw` | `u005.part0000.jsonl` | 186,596,566 | `71e695b88dbc0fb20180ac6f70695f90a56bfdb7130f7f404651e04f511f2111` |
| `sft-math-openr1-math-raw` | `u038.part0000.jsonl` | 176,530,662 | `1518c7b44a6204224458fb44cd1ac0f3a9569ba37f95c2cce66ceceb337e1167` |
| `sft-math-openr1-math-raw` | `u003.part0000.jsonl` | 133,922,001 | `b094db753df34d02724c55141347b7b2659a2ea69ac38b1db4efc8a4d65e2a9e` |
| `sft-math-openr1-math-raw` | `u013.part0000.jsonl` | 126,565,212 | `c295bb8bd0701e7587d776ff0da43bf89ad5654b5c3154ffadd078d4f3304966` |
| `sft-math-openr1-math-raw` | `u002.part0000.jsonl` | 136,062,553 | `7a8d932f5f6c0105ef7dcb8757d695d96c178f1911874531271e26cbfd997f11` |
| `sft-math-openr1-math-raw` | `u034.part0000.jsonl` | 86,667,240 | `13dcd91768442c86a85a723a6530a1abe0225f49f3274baa99938d47ee6a5d65` |
| `sft-math-openr1-math-raw` | `u035.part0000.jsonl` | 93,354,791 | `350cc1c4627eca3d332b36020a398ef7a8797790f2a069a1d29eccc832bd077b` |
| `sft-math-openr1-math-raw` | `u020.part0000.jsonl` | 87,570,519 | `9d4d6751cf6cb9d600f7d9d359bf5d38404e647ff80725c53e0d1b6bdc1c634c` |
| `sft-math-openr1-math-raw` | `u016.part0000.jsonl` | 87,123,528 | `0e94e60a1e7e6e94a526678d4dbfba016ce4c98de95672d504650cc0e2e2e92e` |
| `sft-math-openr1-math-raw` | `u019.part0000.jsonl` | 87,560,526 | `e3165eb8a6c55d954d1f0a74dbe4ddb015bea68dd0ba2d8580003bfaa0f4560a` |
| `sft-math-openr1-math-raw` | `u030.part0000.jsonl` | 86,479,177 | `6f3bb4f726b989f81159932e523bf4679b8596f396ce1dff205388852efa9948` |
| `sft-math-openr1-math-raw` | `u033.part0000.jsonl` | 87,573,827 | `60440dd8497ae249a86086606ab533c3b55c505ebd7baf593481ab0971ca994f` |
| `sft-math-openr1-math-raw` | `u031.part0000.jsonl` | 86,440,695 | `a217a48c0aed40c86b74e31f700b7a46177c65248c858d78b5c64d9f2d44c787` |
| `sft-math-openr1-math-raw` | `u028.part0000.jsonl` | 87,688,375 | `ca4a09a62df36154d434c9eee6ed5d247733f739ffed7aff89c615676eb2999d` |
| `sft-math-openr1-math-raw` | `u023.part0000.jsonl` | 86,946,828 | `9dc1ef2c7bff9318fb0f12651554349dea344bef9dd751cbe0f573604d7b94fa` |
| `sft-math-openr1-math-raw` | `u026.part0000.jsonl` | 85,550,762 | `065843dacc68e5de048ae714a790c3d407410329896ca1584328a84204d4783d` |
| `sft-math-openr1-math-raw` | `u024.part0000.jsonl` | 87,671,860 | `3ac26b196465429712ea99a6dd6f1ef5d1f65b709855424d6bdf218676999f3d` |
| `sft-math-openr1-math-raw` | `u032.part0000.jsonl` | 87,645,776 | `a87dc26f789bbbfefb064794ea6369b72dda2300426f665242a1e93761ec5b4e` |
| `sft-math-openr1-math-raw` | `u018.part0000.jsonl` | 85,940,673 | `e1d2720651a6cfd8dc320cd74a063419f09419dfa813767e8d28d2ff1fa5d639` |
| `sft-math-openr1-math-raw` | `u025.part0000.jsonl` | 87,044,489 | `dc0814e36f40bdc0ce8f6ff23f177a8c917dfc60406881a3c4d1ff0dafdf00e4` |
| `sft-math-openr1-math-raw` | `u022.part0000.jsonl` | 86,346,272 | `ed8d796f709d795387af5c027a5882f39b0b190b5d32ded489c5cf9b7cffb986` |
| `sft-math-openr1-math-raw` | `u021.part0000.jsonl` | 86,461,147 | `0272d6bd42c64c5dca1b950c15dab2d35db74feabad4090d7aae788c0167d3d8` |
| `sft-math-openr1-math-raw` | `u029.part0000.jsonl` | 87,530,949 | `e9e946cd67ff00b08efa63d5089446a5e7e57e9ada77017ee4978335856881da` |
| `sft-math-openr1-math-raw` | `u027.part0000.jsonl` | 86,741,896 | `2810eeca50a2fd909ae2d268203f467c274b849903c24b91435374e91adeede7` |
| `sft-math-openr1-math-raw` | `u017.part0000.jsonl` | 86,358,279 | `624fbfa7d77d26e1408d7f4cba8f19f3e650f9fa16b66f85f099abaeab829bbb` |
| `sft-math-openr1-math` | `u001.part0000.jsonl` | 164,760,896 | `a2a7ca7ed491d67627bea3df52bc8af652080b5e07d26addafc2db70f7fede9e` |
| `sft-math-openr1-math` | `u011.part0000.jsonl` | 165,560,381 | `626788110033364273165288e81585906e79acf97ea3ebdae50ba25058878427` |
| `sft-math-openr1-math` | `u017.part0000.jsonl` | 165,282,504 | `087c24de3bafcd2b93e4373acdd0296c663b745a438fb57671271e7462d4be6a` |
| `sft-math-openr1-math` | `u005.part0000.jsonl` | 164,801,471 | `1cb8d818957d5efdde8745cf759631166616063838da74fca1da538b87b4459a` |
| `sft-math-openr1-math` | `u008.part0000.jsonl` | 164,358,965 | `36649a5b08403330ac0ed51ee07c0523c4e3ffa25180617887e26e40c3d1fc15` |
| `sft-math-openr1-math` | `u016.part0000.jsonl` | 164,618,033 | `aca83ad1c95bc8774defa402951e4c7d37f0c2992675f4ba964c655a2f6c3b69` |
| `sft-math-openr1-math` | `u010.part0000.jsonl` | 164,021,158 | `915703d0931d91af8812cee5f8c1252ce12e1508f85f965d80dacad818993cf7` |
| `sft-math-openr1-math` | `u002.part0000.jsonl` | 163,929,606 | `5320e931abe03ec2cf37ad9c1555f05933c233c7ad74b14bdeb8d43e45a0b2e7` |
| `sft-math-openr1-math` | `u018.part0000.jsonl` | 163,567,923 | `fe3242c643956938787d2c05f3f73259d929f51849be7c1f8e3711da502322d6` |
| `sft-math-openr1-math` | `u007.part0000.jsonl` | 163,285,749 | `6806e7ef2c5a7d0c28a00b2128e3b9cdaeeea3cecb089cdd083c02f1af254d3d` |
| `sft-math-openr1-math` | `u006.part0000.jsonl` | 164,388,491 | `7d59a9ccb5abf2ec36efdbe28b27a56ab1c1f3779e8874257c51a2de53150b72` |
| `sft-math-openr1-math` | `u009.part0000.jsonl` | 163,829,207 | `7ed955a660b37f52e0d4917eb676ccf7cad0bbbd8a849f689555351230bd416f` |
| `sft-math-openr1-math` | `u000.part0000.jsonl` | 163,630,594 | `60ced059bc1df6691124c3bf31b8dd0ff7fa0149c86977a73379f1e7a370afc0` |
| `sft-math-openr1-math` | `u015.part0000.jsonl` | 163,388,108 | `8ce74858ab2407fe37ba46f5cd8024a98e70a3d42ba765b3bc6865456d19411d` |
| `sft-math-openr1-math` | `u012.part0000.jsonl` | 162,903,741 | `62a6479602a6edb1bcf622d33f5972aba2f4178b01def83baca581ed43700b2c` |
| `sft-math-openr1-math` | `u004.part0000.jsonl` | 162,897,106 | `edc0864c95975ae24e8f82412aed74487c29eefe0ac63aad4d60c2aa27fcbf1a` |
| `sft-math-openr1-math` | `u013.part0000.jsonl` | 162,878,576 | `56f347a083ba636828279f5590f5c8e6f4f89bf0a3e7cb686ba34e26ff6b1180` |
| `sft-math-openr1-math` | `u003.part0000.jsonl` | 162,609,635 | `bb16ee687f274dadb33e2e95082d255e9d592d514425f118a7cf461a45eec7a9` |
| `sft-math-openr1-math` | `u019.part0000.jsonl` | 162,790,199 | `de357d23c684f16ff0c0f74f05964110d834360b9c8d8c886106a0bb83b47bb0` |
| `sft-math-openr1-math` | `u014.part0000.jsonl` | 162,564,725 | `1fe2737b3b2e8a879614050338b127bfa752e5949fad42e943c6e2c45d2ad739` |
| `sft-oasst2` | `oasst2.jsonl` | 20,182,471 | `04ef702f982f8e289223e08b1e9350b111f0266a43c64a871965921c3185ee85` |
| `sft-rl-math-openmathreasoning` | `u094.part0000.jsonl` | 300,007,984 | `e50eff427cca942db5b995a50cf75d0495f161d2b01967cb340b16e9874d149b` |
| `sft-rl-math-openmathreasoning` | `u108.part0000.jsonl` | 300,000,406 | `5723025cc31dc9e0cd2336920a495136e0ea1208bad2e4ba02de8c208cb45603` |
| `sft-rl-math-openmathreasoning` | `u094.part0001.jsonl` | 219,430,477 | `44511464ff6ab6ac5d72e6cdbfe848d050f8ee01c0cee6c0e29c39f2b6bf004f` |
| `sft-rl-math-openmathreasoning` | `u108.part0001.jsonl` | 219,333,244 | `68ad4376aadf4cfa1c65359d7f508369ee240e2c11612ede8528b14d078b8603` |
| `sft-rl-math-openmathreasoning` | `u120.part0000.jsonl` | 300,008,393 | `0a1e0f01002660a90439659158ad69c5a83ceb9bd39bd8dd26a83bfd8add1baa` |
| `sft-rl-math-openmathreasoning` | `u020.part0000.jsonl` | 300,008,038 | `5db993a5942ad08e20798553d1bcb7551aacef66940c9e179b8734df943718db` |
| `sft-rl-math-openmathreasoning` | `u120.part0001.jsonl` | 217,790,752 | `048f59ce2763007b08301d0e61353cf93561d50df6ed24fe264f9adfd2125c60` |
| `sft-rl-math-openmathreasoning` | `u020.part0001.jsonl` | 216,931,281 | `6f149ff58416f680af836d81feef1f15f0462b6005cb90ede6cff0ad1744a4bc` |
| `sft-rl-math-openmathreasoning` | `u003.part0000.jsonl` | 300,011,715 | `8843561f0fb67229ae504f787500bcbafb50bba0fdaa853e2c5bc4cb30c75163` |
| `sft-rl-math-openmathreasoning` | `u003.part0001.jsonl` | 217,806,788 | `50c985dfcc68e72f72cced52119f062ba0d06151bdf44785370d0956e3d0add4` |
| `sft-rl-math-openmathreasoning` | `u124.part0000.jsonl` | 300,017,502 | `916174a129450ad815fc6e7ae4a06b960c2b26104ddcb75d35460b7a7e345934` |
| `sft-rl-math-openmathreasoning` | `u124.part0001.jsonl` | 217,063,047 | `4555a6d248e309165da6bc2634ce8569c2033f8dc4715f3dd1724cb1577dd9e3` |
| `sft-rl-math-openmathreasoning` | `u104.part0000.jsonl` | 300,008,540 | `44cbb8fb3e4244553835b7bf7d7e984f1c01380c16ca46165a3d02630680aeff` |
| `sft-rl-math-openmathreasoning` | `u104.part0001.jsonl` | 216,737,113 | `7efef3e008ba1b77475bc5624fc77aec60ce55046b46c80178a139329dc4c801` |
| `sft-rl-math-openmathreasoning` | `u143.part0000.jsonl` | 300,018,031 | `dde5002b3ec4fc38ff192f671c47e3024d164591e4e5d268e04c28586ca8973a` |
| `sft-rl-math-openmathreasoning` | `u143.part0001.jsonl` | 216,644,455 | `d3124320554b8f49c20aebd286788bd7cfd7ca642898b1781fcbb39d172f9d1b` |
| `sft-rl-math-openmathreasoning` | `u121.part0000.jsonl` | 300,044,595 | `8d14524962b2f58b0e53d2a70bce0f3f857c00e0a0a629ec2ba442310a0d4034` |
| `sft-rl-math-openmathreasoning` | `u121.part0001.jsonl` | 216,399,314 | `42413421bfdee28a584f82ea0caf3f7e1a6d06d11fd11f225f12f7e0db520a74` |
| `sft-rl-math-openmathreasoning` | `u076.part0000.jsonl` | 300,011,422 | `6c48b19a18d5a259974cdca92379e1f3b0d8b4c1535045f739a7e9e842ee41bf` |
| `sft-rl-math-openmathreasoning` | `u076.part0001.jsonl` | 216,218,920 | `c2c17deeeacaf6f76e20aa041a13b2e7d0219fa417ef764c8fec6cbc8b0de303` |
| `sft-rl-math-openmathreasoning` | `u129.part0000.jsonl` | 300,012,771 | `136dde1ad02b61995a81927383510614110eaf6addd68b691dbf8ec2955887b2` |
| `sft-rl-math-openmathreasoning` | `u129.part0001.jsonl` | 215,856,975 | `f8c5882c2598d3022ac0a28b2a8463381fc0aebb3dfa46b1b12bf8a92076549f` |
| `sft-rl-math-openmathreasoning` | `u032.part0000.jsonl` | 300,011,316 | `459b7d2c225676d6c125f4ed62fbca242d3998ca6c06aefb53d298289ed5798a` |
| `sft-rl-math-openmathreasoning` | `u032.part0001.jsonl` | 216,327,921 | `60ef98440893a7818e49c003aa1b6b713534e34523aad40d2428c6098554f376` |
| `sft-rl-math-openmathreasoning` | `u083.part0000.jsonl` | 300,028,190 | `c25c06eff451111781281252b1e5068c5f3b0e3e37c95a5d9b02c98eb0f2ebb0` |
| `sft-rl-math-openmathreasoning` | `u083.part0001.jsonl` | 216,496,088 | `441893bcdee4f0cd4f8ffa4947d83ac983dc84584f8f06f828a766deb652dee9` |
| `sft-rl-math-openmathreasoning` | `u138.part0000.jsonl` | 300,001,021 | `8d12d2a96a8464253f21f575b1307245aaa8e23c59cb9226c89456e51e3572dd` |
| `sft-rl-math-openmathreasoning` | `u138.part0001.jsonl` | 215,610,045 | `404e3f2f62217a7022a909c34174aaf6a4833a3d096bce948eb971dd634caa09` |
| `sft-rl-math-openmathreasoning` | `u084.part0000.jsonl` | 300,048,894 | `dffb3490b742ac57280331d0a12ab974b7d2a70b968838d4715bd773d3e98426` |
| `sft-rl-math-openmathreasoning` | `u084.part0001.jsonl` | 216,030,927 | `999affad92243edcf94ff23659058605b4141a63f519390597910f096516d3cb` |
| `sft-rl-math-openmathreasoning` | `u018.part0000.jsonl` | 300,016,999 | `a6640e174b53fc5a92363b0abd58ef8fb8242b3a663cb15799380e3f22110d31` |
| `sft-rl-math-openmathreasoning` | `u018.part0001.jsonl` | 215,807,858 | `5751744130e84009022b40f984fd5dc59e165666fc92f67261b4f7b8160068fa` |
| `sft-rl-math-openmathreasoning` | `u006.part0000.jsonl` | 300,038,763 | `0c05ff085703849fc55d87c3b6abd236b4f27bd0f64dd8f808f76b341b4ccfae` |
| `sft-rl-math-openmathreasoning` | `u086.part0000.jsonl` | 300,016,736 | `21ea94cfeee428a0b681ecd49d31b2fd460643ac07ae875b253bd791ce31a910` |
| `sft-rl-math-openmathreasoning` | `u126.part0000.jsonl` | 300,010,236 | `af4c0cb3c7f2f415f81975d95ed1eb4fa742962c5ac68075a48f3870e9367ad6` |
| `sft-rl-math-openmathreasoning` | `u006.part0001.jsonl` | 216,367,857 | `e559bdc4f52ce06a8c3c17422f8bd727a14a0e70f4dbe343b801da2d9a7d1b67` |
| `sft-rl-math-openmathreasoning` | `u048.part0000.jsonl` | 300,041,202 | `7ed9edfb693e616c4a86de096ed615ea5f796ca8287f51f23e4f04449c0944c0` |
| `sft-rl-math-openmathreasoning` | `u086.part0001.jsonl` | 215,726,639 | `f592e2ab7717f0f42d1b96fd341a4d1a3579dbf9be2f12b43029eef35ae708b0` |
| `sft-rl-math-openmathreasoning` | `u126.part0001.jsonl` | 216,034,408 | `7e2d3e8add0efc02d350b0752bc9c4e8d9e0bdb61c99aec23ac01a49a1eb934b` |
| `sft-rl-math-openmathreasoning` | `u048.part0001.jsonl` | 215,449,752 | `550b4502726c0edff8fab20c8eea3e2a474d740a3c25bfea96015f729716058e` |
| `sft-rl-math-openmathreasoning` | `u141.part0000.jsonl` | 300,022,977 | `4702945bb3e8da24846755b0d686f91f8b4410c8c7499290b06181d63e3ccbac` |
| `sft-rl-math-openmathreasoning` | `u001.part0000.jsonl` | 300,024,199 | `4d414136326fd43b427757f5cf48d2eaa9feaf88fa7143d45fe5886a7d10acbf` |
| `sft-rl-math-openmathreasoning` | `u046.part0000.jsonl` | 300,002,131 | `a35a89680669791ca4b987653c648bcba14cfbaadb0ce4d77e75675094d5c97c` |
| `sft-rl-math-openmathreasoning` | `u141.part0001.jsonl` | 215,070,692 | `9e632a088032b33cf4f24be84b770e991cbf206325b86d03cdc3ea5747390cff` |
| `sft-rl-math-openmathreasoning` | `u039.part0000.jsonl` | 300,018,424 | `ad37bc7d15882cca5f63a7886dd255ed6491c1639c1b7bac0aef35d6f0b947c0` |
| `sft-rl-math-openmathreasoning` | `u001.part0001.jsonl` | 215,399,449 | `a1f38c7bf7b79e668e3a70d1e57e4c678480797e214b264affdab37258f507e8` |
| `sft-rl-math-openmathreasoning` | `u046.part0001.jsonl` | 215,444,408 | `432de594693c3360310be10482e8cc18073a77c1c1215d25efc0503acc86310a` |
| `sft-rl-math-openmathreasoning` | `u039.part0001.jsonl` | 215,059,389 | `0f0e10b467f5cc58267979a500a830259a9e12c46b500fcec2bed43e98016f6d` |
| `sft-rl-math-openmathreasoning` | `u095.part0000.jsonl` | 300,008,856 | `6a52e3d74ffd5bede2620f048b0f1af524d982b5cb0cacc95be2ec4b0536f902` |
| `sft-rl-math-openmathreasoning` | `u025.part0000.jsonl` | 300,014,540 | `19cf7adf5d9fc4d9fc540554167817976ff8fbf183cecc0aac0356f0b34b17cf` |
| `sft-rl-math-openmathreasoning` | `u101.part0000.jsonl` | 300,023,589 | `9178f310149ea900ada7aa1ac564515c9793025f60e209e43c47eb996dc2da87` |
| `sft-rl-math-openmathreasoning` | `u017.part0000.jsonl` | 300,005,761 | `e283b018b2e8f449191b21a3c01b0066235a20e61e653b09bada616cc75c4b22` |
| `sft-rl-math-openmathreasoning` | `u025.part0001.jsonl` | 214,637,199 | `78dd775f023d2e5a21e2cb2d6d7ab8a592da6fa97b9bbcb309a8d80a1c8d9ff8` |
| `sft-rl-math-openmathreasoning` | `u095.part0001.jsonl` | 215,218,790 | `06769fd1a484ac93a948c75c05de1ea5ae411f209ae7ff8bbd884de1a2c8e1a9` |
| `sft-rl-math-openmathreasoning` | `u101.part0001.jsonl` | 215,137,490 | `3a79d870bc919f740c7da58802d6f57f241220c455695a4ff8dbfe25ed78e406` |
| `sft-rl-math-openmathreasoning` | `u017.part0001.jsonl` | 214,529,626 | `67435259fbfa7309594bdffbba7679a6576be79d6651908baf8163ed1ffbda9c` |
| `sft-rl-math-openmathreasoning` | `u127.part0000.jsonl` | 300,006,204 | `a3fedf57b7243f5a23cca8527449b286b322408027897d6fccfe1c253ea29540` |
| `sft-rl-math-openmathreasoning` | `u072.part0000.jsonl` | 300,015,272 | `6990aa5a280cc59435245885a987b91be483e3c8056159d10b1ee315ebbcfe20` |
| `sft-rl-math-openmathreasoning` | `u033.part0000.jsonl` | 300,037,146 | `7c2f8ea07b49fb20bf1bc3694e67292a8168f010e1777e415b79893ab473464c` |
| `sft-rl-math-openmathreasoning` | `u127.part0001.jsonl` | 215,071,520 | `9f7761e46e3410814c0565efa38658ca6fa65c6ee64261cb736d6cae4ff7d0ec` |
| `sft-rl-math-openmathreasoning` | `u016.part0000.jsonl` | 300,011,434 | `3c9d00964fb102b6ea4c50cb413d07a86a0f822ebbe9a37fca6677d9fb9686f2` |
| `sft-rl-math-openmathreasoning` | `u072.part0001.jsonl` | 215,069,199 | `599e11d62e44cbd5761d70693d83d733f9b34ad31dcc6228247e0d23abd9a7d7` |
| `sft-rl-math-openmathreasoning` | `u033.part0001.jsonl` | 214,743,909 | `29fe0fd975f744bf8b89bd78336fd787e6e77f7fadbd7bb8a2e6a8d440e2f9c6` |
| `sft-rl-math-openmathreasoning` | `u016.part0001.jsonl` | 214,586,974 | `19ca34f97d43636c33793f62bf58ea7c94e9f857c64570ec137cd3313770ce01` |
| `sft-rl-math-openmathreasoning` | `u050.part0000.jsonl` | 300,029,312 | `b47a8e504ebec306052397ce5829efbf6043578014b2680e246e50ee4abbcdf9` |
| `sft-rl-math-openmathreasoning` | `u109.part0000.jsonl` | 300,010,947 | `9d2b08fac5d15db19ca56f7bdb666d9958efd020a65b06990f2d3ddb49005369` |
| `sft-rl-math-openmathreasoning` | `u098.part0000.jsonl` | 300,006,668 | `0b9f88cd2e6dc7c0da546a8e4d434bf795102a58f70ddff3bf743c9e303266f0` |
| `sft-rl-math-openmathreasoning` | `u050.part0001.jsonl` | 214,877,380 | `1d1fc824836518211e8d85532737420534fa57a421e4340a7e8ed136336a19ca` |
| `sft-rl-math-openmathreasoning` | `u022.part0000.jsonl` | 300,002,607 | `f48bb7e2a94ff336b7afc71f18549784ced06dbb4adda3f1f2f40475345aa4eb` |
| `sft-rl-math-openmathreasoning` | `u109.part0001.jsonl` | 214,962,734 | `40f4fc3cd65a309468352a4b714e60fb9eeaed5c3780e0b1257f06efab6c18cc` |
| `sft-rl-math-openmathreasoning` | `u098.part0001.jsonl` | 214,585,329 | `9d4ac8a026f4d3e057645a8cb513a7a7e50da8a14461c783dfebf82d1b2be8ea` |
| `sft-rl-math-openmathreasoning` | `u022.part0001.jsonl` | 214,432,085 | `5d6dfcdefd4d530a72410089bafe23ae926cf268ba5ff381f0a6bb8b96f505f2` |
| `sft-rl-math-openmathreasoning` | `u035.part0000.jsonl` | 300,025,508 | `ef080ba8e532761f9aec7fd455f9564cc67a9bda689d64bdb63a386e14a77654` |
| `sft-rl-math-openmathreasoning` | `u140.part0000.jsonl` | 300,000,643 | `0709cc334a76078a544dcf51e82d89eb9b0cb6a11f3c8ea8354954482a4626ac` |
| `sft-rl-math-openmathreasoning` | `u093.part0000.jsonl` | 300,017,371 | `5550149b03c168baaa0e510ac6e6830606abd96b466d24c33bc1f7a023048b89` |
| `sft-rl-math-openmathreasoning` | `u035.part0001.jsonl` | 214,706,027 | `c89115b3ace6150b81493cdf5e0e1b8600c3a5dddc31a1f01b05a64e280e56de` |
| `sft-rl-math-openmathreasoning` | `u061.part0000.jsonl` | 300,027,142 | `63a9db0a7367c26a83ef403b043a8dbd98739cece9516787433648d1becba225` |
| `sft-rl-math-openmathreasoning` | `u140.part0001.jsonl` | 214,761,897 | `a4cd34f5e22eaf887518c5bf126f3d7e9ec20991ac17651c954471255148069c` |
| `sft-rl-math-openmathreasoning` | `u093.part0001.jsonl` | 214,709,207 | `29ce6493daddd55eb1da160787c5bf592939483e83495d33bdb32d52e2f8749f` |
| `sft-rl-math-openmathreasoning` | `u061.part0001.jsonl` | 214,809,126 | `dd14be7dd2c4c4b825c5f5033d90778abc07a1d53401da60e3c0d28e25353630` |
| `sft-rl-math-openmathreasoning` | `u092.part0000.jsonl` | 300,007,498 | `dbf877d5c2a6ca7af54437258cf654b72f8cb3581ac2918dcaa8b016c110386a` |
| `sft-rl-math-openmathreasoning` | `u078.part0000.jsonl` | 300,001,063 | `d391ef107fe505d95a59dc1a6ce6bc77225e64e4dfbfa68f9a9186c364d30322` |
| `sft-rl-math-openmathreasoning` | `u090.part0000.jsonl` | 300,003,355 | `de6fcaab2a8259ca0ba7d4085da92fe8ec75c6ee067fac8abdc81d5eb7044b2a` |
| `sft-rl-math-openmathreasoning` | `u043.part0000.jsonl` | 300,013,485 | `e900d875d227132496e514199f3b06625e4478013025d092966b72826b31d062` |
| `sft-rl-math-openmathreasoning` | `u092.part0001.jsonl` | 214,669,015 | `9dfb9b510ea6c811f707f5742dd87abe6a67e7539f99d5fa2339672121e6d3eb` |
| `sft-rl-math-openmathreasoning` | `u078.part0001.jsonl` | 214,415,084 | `559634ab4d2730567df213928c6bee01a2b8063bab735b5810c9461fd0fbd455` |
| `sft-rl-math-openmathreasoning` | `u090.part0001.jsonl` | 214,661,607 | `6a9c48a500addb75a94229cc42e088f28c40b8cafa6bc78ede171731e5a53d79` |
| `sft-rl-math-openmathreasoning` | `u043.part0001.jsonl` | 214,399,561 | `72b135469e25a4d4c2eba037d12653529d2aa1390c071bf723b60e93d05dcbf4` |
| `sft-rl-math-openmathreasoning` | `u029.part0000.jsonl` | 300,007,339 | `44a20038e7c9a38b73f936ba2f9ed67d9d268d029e76737a502c85435d969426` |
| `sft-rl-math-openmathreasoning` | `u002.part0000.jsonl` | 300,002,307 | `c50f11183be03f461fbd86cdb331566c49c9a6b4a389489215295dbcc480cf67` |
| `sft-rl-math-openmathreasoning` | `u014.part0000.jsonl` | 300,005,958 | `61140d9913b3a1af089db82b9b45d93f7844657a1189cc06b3d995a416b85b94` |
| `sft-rl-math-openmathreasoning` | `u029.part0001.jsonl` | 214,495,270 | `329737a03b0561883e85aa736787925a72d620f3be374e0332f70f12d9263fc8` |
| `sft-rl-math-openmathreasoning` | `u142.part0000.jsonl` | 300,011,018 | `644b88c1941c8ef6a971a6eebc664b482e1996fff50d9c675436e260c95d1ca7` |
| `sft-rl-math-openmathreasoning` | `u002.part0001.jsonl` | 214,808,899 | `a344afa1ce27a2eb380ee10a1ed7a310936c7e12379d28fe117c20720b6e580b` |
| `sft-rl-math-openmathreasoning` | `u014.part0001.jsonl` | 214,827,587 | `99e4e4627a898c45902e9b59018abb3d75db769cb384d09b8813f054d8a095e0` |
| `sft-rl-math-openmathreasoning` | `u142.part0001.jsonl` | 214,666,475 | `ae332a0b33998589b0a98114f3f80adde33872a867bdddf36cb132178015ce10` |
| `sft-rl-math-openmathreasoning` | `u082.part0000.jsonl` | 300,012,098 | `22e2596a1f367659442dc07afae7ed4b44f3c4d1067d0b3ed254a3aa795e8386` |
| `sft-rl-math-openmathreasoning` | `u042.part0000.jsonl` | 300,017,905 | `5e18c6c54d47a4c1fac476b00502ad0579ccec571f60bff9b47343b92891a960` |
| `sft-rl-math-openmathreasoning` | `u085.part0000.jsonl` | 300,013,306 | `8ad8c145dee8ad84b8eff8ebb82426b586a0f879e6a8a047ba0bdf202ffec239` |
| `sft-rl-math-openmathreasoning` | `u082.part0001.jsonl` | 214,547,401 | `4cc68f11c460709c1bf49b84ee68a21bf718311ce33dff0580da90c39ce2c38e` |
| `sft-rl-math-openmathreasoning` | `u070.part0000.jsonl` | 300,015,552 | `aaaea1f61d56fe1c4913f2b9ddc56afb424351734529764cab1f66564d4fda67` |
| `sft-rl-math-openmathreasoning` | `u085.part0001.jsonl` | 214,124,736 | `249a0f2b1387a4daa72a739a4f11d61cf6989ee556afc200c652e6a4a3f71ae0` |
| `sft-rl-math-openmathreasoning` | `u042.part0001.jsonl` | 213,998,839 | `5464898dcf3d69e913120a5184cdccf1b375f45d389dcbef06294281c5a7d172` |
| `sft-rl-math-openmathreasoning` | `u070.part0001.jsonl` | 213,946,144 | `49d357a24ea39208b2df42eead2d9e2456a80e1493a48dc61b7122119213edd2` |
| `sft-rl-math-openmathreasoning` | `u034.part0000.jsonl` | 300,003,551 | `4a8544f69f89483da2aa879bfbf89e603f3ebe4e7056113f51703a97217b303f` |
| `sft-rl-math-openmathreasoning` | `u015.part0000.jsonl` | 300,001,868 | `feb81afe0601700a90f88452d1bba71bd799f4d2042692a0de02b2e3a4f53ffa` |
| `sft-rl-math-openmathreasoning` | `u055.part0000.jsonl` | 300,023,812 | `8732c9bc0765e9d84a2df39d8e0cb39d984efd8d9d70df73340ec20e64a2e0c1` |
| `sft-rl-math-openmathreasoning` | `u034.part0001.jsonl` | 214,533,383 | `186054ad5841bb0b3592c03a05701082c6cb4b51f410c4a020d96a4cb5dae7d0` |
| `sft-rl-math-openmathreasoning` | `u132.part0000.jsonl` | 300,004,633 | `907ec43ecf50f6f4fd4a030e728c4b25b7e1444382448f06e57ed66807d79c1b` |
| `sft-rl-math-openmathreasoning` | `u015.part0001.jsonl` | 214,200,749 | `4fe8ea57b742bfa24e6bb44c079c48a556d0be7e636a40ede5e50505c53034a1` |
| `sft-rl-math-openmathreasoning` | `u055.part0001.jsonl` | 214,275,113 | `5a40d7fe839b65d6cf789f565d12314ecdd955b08ae9d236b26ce0922f986337` |
| `sft-rl-math-openmathreasoning` | `u132.part0001.jsonl` | 213,976,077 | `0e0ba283fc141f3b394458beab81cac1e0ab90c8f783a3a77ffef2a5b27d9aed` |
| `sft-rl-math-openmathreasoning` | `u071.part0000.jsonl` | 300,007,356 | `4ed72d4d443e21c97158ee4354e16f69048972792ccca4c7650c1e8f76332e3b` |
| `sft-rl-math-openmathreasoning` | `u063.part0000.jsonl` | 300,023,923 | `40311a80f6c5e2c20bec60f766b60a5c8d6da7408db7bdce8fcae905a5b36fb1` |
| `sft-rl-math-openmathreasoning` | `u116.part0000.jsonl` | 300,001,052 | `edd68e2a69ca1237cfa992e77c2ea87d2fcf52c73e52644cf87978895da8ea8d` |
| `sft-rl-math-openmathreasoning` | `u071.part0001.jsonl` | 213,404,809 | `8698dc99aed68cd272c664472616013f23c8838a4603165b4352d6e1294b4b46` |
| `sft-rl-math-openmathreasoning` | `u087.part0000.jsonl` | 300,016,032 | `85c6f618afbe9f90eb8ad05a4ee7d15fc7c19c432ca842c354f8f55a025657d5` |
| `sft-rl-math-openmathreasoning` | `u116.part0001.jsonl` | 213,981,774 | `05b0ba32e3dfce81d3713f066b5e6391c65a3c65f37a439e76c19498575a65ae` |
| `sft-rl-math-openmathreasoning` | `u063.part0001.jsonl` | 213,789,820 | `72e2a1734a2e108ac52b6a1d301f4d7ac7d283fa5a26aaa415cdc6599fbb42c6` |
| `sft-rl-math-openmathreasoning` | `u087.part0001.jsonl` | 213,606,599 | `83ef941b1bb7d3e777a84efe9ed6e38026e8673ae0549f82389cb396d1ff7e8a` |
| `sft-rl-math-openmathreasoning` | `u133.part0000.jsonl` | 300,020,330 | `9bd1e0892249832722fa35bb27859ba44633e2ce6e091cc32d87d27b393bfade` |
| `sft-rl-math-openmathreasoning` | `u079.part0000.jsonl` | 300,015,733 | `5574b550fe2872c98d04dbc4bbe72732681d988b15e54f24d542097568e88212` |
| `sft-rl-math-openmathreasoning` | `u118.part0000.jsonl` | 300,017,442 | `ed3b625fef7bffd386a24edad6512ec485f6c96058ae22b83d23445ef210113e` |
| `sft-rl-math-openmathreasoning` | `u133.part0001.jsonl` | 213,831,122 | `457da800fe0b90483e5ef0c046f2d7d60cbb1d0daf2c821178ecf809b35d5568` |
| `sft-rl-math-openmathreasoning` | `u031.part0000.jsonl` | 300,018,123 | `2ad9dbcff4755d80f87c3bbd9cd63750b7d98e5bb166294bd3156ea9bdf264c9` |
| `sft-rl-math-openmathreasoning` | `u079.part0001.jsonl` | 213,899,711 | `58bae34330741436a67fc575378d79fa399bdc53f3eb605a38889e897e903189` |
| `sft-rl-math-openmathreasoning` | `u118.part0001.jsonl` | 213,764,318 | `b3b1ec176289ef5bd289b68d2599972abfdcc5a0de106afe1008e8bb65c19a63` |
| `sft-rl-math-openmathreasoning` | `u031.part0001.jsonl` | 213,664,295 | `239e894708ef2a74325c897699cfb4e1206a034a7db9ba2489c5872628669630` |
| `sft-rl-math-openmathreasoning` | `u028.part0000.jsonl` | 300,008,474 | `d617e965e1c4ff663bd8bc064762697663d9ef0e67641012939a50b22e80a4d0` |
| `sft-rl-math-openmathreasoning` | `u041.part0000.jsonl` | 300,009,869 | `2a7e3898c8c6941c76a1943eef0fe8ee098497c59fd452a86a5b92a833c20154` |
| `sft-rl-math-openmathreasoning` | `u044.part0000.jsonl` | 300,023,823 | `f09492faeb8f93732191dd7f26bd0abcfdab3ac1328678069da8dc6ba181d29f` |
| `sft-rl-math-openmathreasoning` | `u028.part0001.jsonl` | 213,511,319 | `55e92b17e8579f63060cf02c141b66439de5e965eb65b0529fde60b0177fd5da` |
| `sft-rl-math-openmathreasoning` | `u041.part0001.jsonl` | 213,260,392 | `0fda2a2c8114adf1a4acd4d7dabc84ef19e1f1b6e4ad18fcc46a9292dc1af745` |
| `sft-rl-math-openmathreasoning` | `u007.part0000.jsonl` | 300,009,268 | `80ff9577b746b9f1655e698833e851a51b045aaef4d70c840f5313fcff6cb324` |
| `sft-rl-math-openmathreasoning` | `u044.part0001.jsonl` | 213,449,195 | `fe6100b280a0ab37175ba21066925f9bd23de0957a7216a52b4b8fa5959cf6bc` |
| `sft-rl-math-openmathreasoning` | `u007.part0001.jsonl` | 213,643,474 | `230903ba0613fd9e34f5471f099869453f51dc2503221fcc7240d30614d3cfc7` |
| `sft-rl-math-openmathreasoning` | `u052.part0000.jsonl` | 300,021,172 | `2432092342dec96e31bf210abe2f6bb077fc1865094723a6f797225e17df8416` |
| `sft-rl-math-openmathreasoning` | `u136.part0000.jsonl` | 300,021,597 | `af3e4a7d767a08d53ff6b97960e89e5a205a7e11ccb7a7fd8af703cd6c6d5926` |
| `sft-rl-math-openmathreasoning` | `u111.part0000.jsonl` | 300,012,270 | `60dd6b18bd0c9e1490924a177e0b4ed9984dfeb9f3f1d6c2996d75215a90923f` |
| `sft-rl-math-openmathreasoning` | `u052.part0001.jsonl` | 213,785,302 | `574ece59baeec2caf1ad0a86dcb68c26228b563835811bcc618f213a5f3d1670` |
| `sft-rl-math-openmathreasoning` | `u065.part0000.jsonl` | 300,000,820 | `12528ad746234ee8c8ebd423aaa43ce274cedf2402a3394f9de63d7b51ed6260` |
| `sft-rl-math-openmathreasoning` | `u136.part0001.jsonl` | 213,369,343 | `6130437fe5b8995de9190bb0332df944cf81cf6724fff870fb643e792c06cf50` |
| `sft-rl-math-openmathreasoning` | `u111.part0001.jsonl` | 213,484,021 | `0604a8defcc46648bdaf87b725e12d93b5432b2f1a0375d54b99343e0b8fc2ad` |
| `sft-rl-math-openmathreasoning` | `u065.part0001.jsonl` | 213,812,322 | `e5ac0ada6becffb312032b7daafe0fb85a68228095191fafa23ec41823efcfe3` |
| `sft-rl-math-openmathreasoning` | `u010.part0000.jsonl` | 300,001,112 | `aaa170c494299faf5f5e2ddfddcbd6918510178ebcfbfc7144c0791f142839f2` |
| `sft-rl-math-openmathreasoning` | `u051.part0000.jsonl` | 300,008,049 | `6d0dd1b58b3b2c8f3f732891446b3eec0602d65fb65bb2485640e41adc907111` |
| `sft-rl-math-openmathreasoning` | `u062.part0000.jsonl` | 300,049,810 | `af5c959a916f812ffb83bdbf971e02bedccb6972b606758fbf391c87063a164e` |
| `sft-rl-math-openmathreasoning` | `u010.part0001.jsonl` | 213,160,037 | `a4904cc22db2e38991c32bd424118726278db57f7cb0c6684b372c3e7b113d39` |
| `sft-rl-math-openmathreasoning` | `u060.part0000.jsonl` | 300,023,488 | `a680fb31c56089cdbeafc8a76d169ad40a250625b3b82589863632e85ab5516f` |
| `sft-rl-math-openmathreasoning` | `u051.part0001.jsonl` | 213,182,957 | `34aeff0cb34d06ff93dbc2eedd9658ea7234b5b80b289df82911b79516737dcc` |
| `sft-rl-math-openmathreasoning` | `u062.part0001.jsonl` | 213,367,010 | `c0b5b691483b189740033b155b1b55bb6fd50af43926bd6cfe080026b857cd3a` |
| `sft-rl-math-openmathreasoning` | `u060.part0001.jsonl` | 213,585,851 | `89dde4a940cebd6ba1a1aa3a9e86a29a15f47ecdf950337db9f29c8eb96aade6` |
| `sft-rl-math-openmathreasoning` | `u036.part0000.jsonl` | 300,021,950 | `183d48808abe3d4c37640acba7c7312cafc5d99a89c211d8a2efe1b3339beea9` |
| `sft-rl-math-openmathreasoning` | `u005.part0000.jsonl` | 300,001,751 | `e71d116830b5fddffaeeb03455f319b201c21fc5fc9e6a665ba56d8008fbbf5e` |
| `sft-rl-math-openmathreasoning` | `u053.part0000.jsonl` | 300,012,380 | `d2d26ab61d034aa39f2175be75423a5ed01b4b2d8975e7e620a66651ba43b0be` |
| `sft-rl-math-openmathreasoning` | `u036.part0001.jsonl` | 213,341,607 | `b646e23f6b86ea7f073fccdc73412f48baf8df48e0bc04850d92eeceba66b8a6` |
| `sft-rl-math-openmathreasoning` | `u139.part0000.jsonl` | 300,007,123 | `f87d1fdc072d4cc090bf266c75d77eb7d65b38dd9a595896be764abdc9431c2a` |
| `sft-rl-math-openmathreasoning` | `u005.part0001.jsonl` | 213,379,284 | `e0d1910e19f67ef641fd51780707a67ff5e41a32d0a5328f4c5d13e7d271b071` |
| `sft-rl-math-openmathreasoning` | `u053.part0001.jsonl` | 213,030,134 | `1c0e674facc2009a52f3bde7e31a1db7d0255eb77444434a96705f9d26875878` |
| `sft-rl-math-openmathreasoning` | `u139.part0001.jsonl` | 213,131,747 | `cd3d71d862631a7ee050f7a2172b588345960f7fbc111c4bb26af91f2d285610` |
| `sft-rl-math-openmathreasoning` | `u037.part0000.jsonl` | 300,011,981 | `3feb5d7c78993469e805992398d319af37a73e64b1ec9c5147ef593baf6c5565` |
| `sft-rl-math-openmathreasoning` | `u024.part0000.jsonl` | 300,032,023 | `00acb893ae6c797933814c7c4cf53819fbe94cce133dba6fd684d5423247b775` |
| `sft-rl-math-openmathreasoning` | `u135.part0000.jsonl` | 300,027,381 | `93fe88b4682a119e2de701c871eca2169c2c596181fb587670796847775e90dc` |
| `sft-rl-math-openmathreasoning` | `u106.part0000.jsonl` | 300,028,842 | `6bbd923b3bcd8cdbf39a630b03ca5b79c1bdc43c443a497be593c07deb9781fd` |
| `sft-rl-math-openmathreasoning` | `u037.part0001.jsonl` | 213,242,853 | `633b05b656da7f8c15fcea692271c61e4666fde2e6fe20a02f6fb1aed9d3630d` |
| `sft-rl-math-openmathreasoning` | `u024.part0001.jsonl` | 213,195,929 | `a4f9ceb1a4c91be4887995daf51c6c38372857dd28aca6f2216da038be3e5cfa` |
| `sft-rl-math-openmathreasoning` | `u135.part0001.jsonl` | 213,240,395 | `ca9f9b75506657eb91164c8d3bdd2eba2c7d77f270dd881349d47049fb346cd9` |
| `sft-rl-math-openmathreasoning` | `u106.part0001.jsonl` | 213,194,376 | `f6bc6c0b57ccde7dfaddf89de62e10b9651a3caadb3189cb6a0a10b9383ca163` |
| `sft-rl-math-openmathreasoning` | `u091.part0000.jsonl` | 300,023,223 | `390a99c0bc716de6e397766a86ee2964fa4c8a5644b359f823e1b9a86bd703f2` |
| `sft-rl-math-openmathreasoning` | `u119.part0000.jsonl` | 300,035,967 | `7f1a0e7a144da16fd275109ed1959bf96a7c806f7fa899989da97fcf55987f70` |
| `sft-rl-math-openmathreasoning` | `u099.part0000.jsonl` | 300,032,908 | `e21bf8b267f2ab009ed9df159bfb6956699265b8c0a4076c4b82c649980f8513` |
| `sft-rl-math-openmathreasoning` | `u073.part0000.jsonl` | 300,002,363 | `63e7f0478777365c58540e481d8a983c464bc41eb6fbfdea57fd8fbbef099cd6` |
| `sft-rl-math-openmathreasoning` | `u091.part0001.jsonl` | 213,279,251 | `d590c0f7f863b96efa72c1fbdf0c533ef2d6352475585400ef90de6227bdf3cd` |
| `sft-rl-math-openmathreasoning` | `u119.part0001.jsonl` | 212,760,853 | `628899bfc92ab7c544435d1b2a62a95204b8d4caacde9530ba54b2d0cf535306` |
| `sft-rl-math-openmathreasoning` | `u099.part0001.jsonl` | 213,197,040 | `54645cd4e75214ed4d600731b8d235bb1a811ec19a91252c80c16689da45d506` |
| `sft-rl-math-openmathreasoning` | `u073.part0001.jsonl` | 212,939,377 | `e528d434f13cce92eb316ad773b4f90696ef08c434b4f0257305889ce623e6a9` |
| `sft-rl-math-openmathreasoning` | `u114.part0000.jsonl` | 300,011,055 | `47af0167fab58ac537f122322c0be2d48274b0372a99dda7ac6c66411e0a9b2b` |
| `sft-rl-math-openmathreasoning` | `u057.part0000.jsonl` | 300,017,448 | `5b5d9929bdef7a2a971e5443e7696adfe0bf8423aba6c9cf2c843e14704a785e` |
| `sft-rl-math-openmathreasoning` | `u074.part0000.jsonl` | 300,005,913 | `a56c268a1f6aa29b5f32bfbf58a288b0aa334938aa60a9dc8810708ab270f036` |
| `sft-rl-math-openmathreasoning` | `u027.part0000.jsonl` | 300,006,488 | `4f3f365a1bdbc185609ff175b5d09310d5f665e13a95428ac30625556bb98f94` |
| `sft-rl-math-openmathreasoning` | `u114.part0001.jsonl` | 212,565,293 | `019a73525a180f1ffcf698220217ecf341c90bc6d0d03628a0e0e7e589e4263c` |
| `sft-rl-math-openmathreasoning` | `u057.part0001.jsonl` | 212,291,106 | `dd20783689254d09ca010c232fee03f8e2835469c3e381a5b42554b41bf34ed8` |
| `sft-rl-math-openmathreasoning` | `u074.part0001.jsonl` | 212,962,930 | `86d7dd9dbb515c12e91a7a680543418c12e2672ba2b6e47b94cf57e0435908c1` |
| `sft-rl-math-openmathreasoning` | `u027.part0001.jsonl` | 212,981,389 | `0caac7ef14fc86d02dbcff203da5e791130ab566c29ded10db00121f2c63600d` |
| `sft-rl-math-openmathreasoning` | `u047.part0000.jsonl` | 300,004,143 | `3458b7e011afefc72bdb6dfa9521848aeff9bd213497c482ceb8e8abe3ea20b4` |
| `sft-rl-math-openmathreasoning` | `u112.part0000.jsonl` | 300,010,648 | `612ce96f1811b48aa70b4bf3fbd0b5e2cdce4d10571bec3532fddeb883ef30ed` |
| `sft-rl-math-openmathreasoning` | `u064.part0000.jsonl` | 300,012,901 | `eb447ec20a83b159c64401a2265f1a84d5b0ac4215ed794c9e6ad90b46864fea` |
| `sft-rl-math-openmathreasoning` | `u047.part0001.jsonl` | 212,739,301 | `9afe9f87205164c1c26f5a35d379daa69ce1a0ededa90f8b515599922b730ec9` |
| `sft-rl-math-openmathreasoning` | `u115.part0000.jsonl` | 300,022,696 | `e7a7d8b8153a62da9f6f6e39bee1fa039d0f3e85bb671cbbf85f744252631dff` |
| `sft-rl-math-openmathreasoning` | `u112.part0001.jsonl` | 213,223,931 | `954bbf2f35351881f5bf13a96cc5f90ed2219052e93259d7972517c0fd4ecf57` |
| `sft-rl-math-openmathreasoning` | `u064.part0001.jsonl` | 212,989,986 | `4bc7331b75cdaa0ca5f50584a00463530cd7f26b11f2624480dfe04f8fbb238e` |
| `sft-rl-math-openmathreasoning` | `u115.part0001.jsonl` | 212,865,839 | `553889e002ada359536ec3af414ff756b47996703c9140fc6055f70954d46bf6` |
| `sft-rl-math-openmathreasoning` | `u045.part0000.jsonl` | 300,029,888 | `33d50f3dc957f1ba72862854fa7d0d6e72005ea5f3306301ba3d11d8028cb579` |
| `sft-rl-math-openmathreasoning` | `u040.part0000.jsonl` | 300,002,080 | `985bad7df9941270f072013966ca2fe62f1b7fb3881858f817fc601c55e528cb` |
| `sft-rl-math-openmathreasoning` | `u097.part0000.jsonl` | 300,003,681 | `9f029f33aa6f2742f7fecbc4a1c2583c137cfc912d9345472973a0de012b4d94` |
| `sft-rl-math-openmathreasoning` | `u045.part0001.jsonl` | 212,780,571 | `caac1c124981e836a750e87de8c64f7e524230725a2c3c0245af612bf11661a5` |
| `sft-rl-math-openmathreasoning` | `u040.part0001.jsonl` | 212,417,747 | `8c8fd949782287f8b802647f3d75be377ccd133e6ebd902bd6106b367dcc65d9` |
| `sft-rl-math-openmathreasoning` | `u100.part0000.jsonl` | 300,027,093 | `e20a2a5f8601fba1d4b3c2747395534316a2dc3cd9b8230d9de0e11223e69135` |
| `sft-rl-math-openmathreasoning` | `u097.part0001.jsonl` | 212,687,341 | `69b4f7498705ca12c85f3310af108424db7bc7b1940c455d4335a23572a18c41` |
| `sft-rl-math-openmathreasoning` | `u100.part0001.jsonl` | 212,743,541 | `748130d4791fc2cf832477f1ffed2b825d778bce09a8794f108553fa9c1be051` |
| `sft-rl-math-openmathreasoning` | `u130.part0000.jsonl` | 300,020,012 | `cc3e13d6140b51b9d711a048ff993b8a755147e2a37184dcb6db7e0b8e54cc56` |
| `sft-rl-math-openmathreasoning` | `u026.part0000.jsonl` | 300,019,618 | `e2bf36c7fcacb461b8af4f3e87d19c2df02ca34d1141f1b456cb0b3e5b54c9a9` |
| `sft-rl-math-openmathreasoning` | `u080.part0000.jsonl` | 300,033,974 | `eb6acdee871c1988b33b76ef0df0ffd7ccbb54b5661b67720436d16a6d831042` |
| `sft-rl-math-openmathreasoning` | `u130.part0001.jsonl` | 212,654,908 | `4f4589e10e39c53da8328e96e8d43bc306305e2e8a70b9d38b1e2a7811842589` |
| `sft-rl-math-openmathreasoning` | `u107.part0000.jsonl` | 300,016,521 | `4b1602db4b6f957c6274ebe95fdd50831a7001b3e89286c41818921cbd3d0cb4` |
| `sft-rl-math-openmathreasoning` | `u080.part0001.jsonl` | 212,504,346 | `3dad3af17badb3939adea312866909e18b1f305332790e047cae665bf593b4ec` |
| `sft-rl-math-openmathreasoning` | `u026.part0001.jsonl` | 212,683,155 | `97bb6dfcc08b8b4ffda8113a9354c28534f9af3cb7a22b5ed0557ef0a3348783` |
| `sft-rl-math-openmathreasoning` | `u107.part0001.jsonl` | 212,387,168 | `d785ce146062cf7a9705dbc90d0941ac0f29161348d9bcde5fb396748184a3ba` |
| `sft-rl-math-openmathreasoning` | `u008.part0000.jsonl` | 300,005,632 | `1733681f0810a92610a85102225518628f053a96f093e403f5225c948fe59a53` |
| `sft-rl-math-openmathreasoning` | `u096.part0000.jsonl` | 300,013,538 | `ea772257a51cdd03f406db7b1d822a59ec2d9092b8cff95836b3e6192354f62a` |
| `sft-rl-math-openmathreasoning` | `u038.part0000.jsonl` | 300,014,762 | `f6e00674eddc81cd174b7b22a4626d23e14ec9a51d831591484496ed9b6f2ce4` |
| `sft-rl-math-openmathreasoning` | `u008.part0001.jsonl` | 212,590,083 | `c570ee5d68bd743d58e083a3a91ca5909514c44255f5589706800c92e5f85681` |
| `sft-rl-math-openmathreasoning` | `u128.part0000.jsonl` | 300,025,380 | `aff3f2720cde7bf6fae09b4f6eb5898fe19b9dee325d868bac50c9d0fc20848f` |
| `sft-rl-math-openmathreasoning` | `u096.part0001.jsonl` | 212,286,317 | `979507a86a8bb0fde10c9ded70fcbb84eebddaf5e5c48775a10dc540abe0f8c4` |
| `sft-rl-math-openmathreasoning` | `u038.part0001.jsonl` | 212,332,590 | `c466a2679001c7786ce9eb34146f7825c06335a14ce6f5cc85d1e6534e7760ff` |
| `sft-rl-math-openmathreasoning` | `u128.part0001.jsonl` | 212,412,524 | `4ace20673fb9b07d162ae1a5ffc81027c687f80510e35ffb264e26c11a0b0d1c` |
| `sft-rl-math-openmathreasoning` | `u102.part0000.jsonl` | 300,002,848 | `8d70776eb1daee4330be634e9276ecbc57f409cc9bd2ae7bf26005ae2440b0fb` |
| `sft-rl-math-openmathreasoning` | `u122.part0000.jsonl` | 300,007,597 | `a0397b82a6de3d5ef13f96b8e3795f5ec59adc021a5f1f1bfa99f55670f801b5` |
| `sft-rl-math-openmathreasoning` | `u069.part0000.jsonl` | 300,004,730 | `bc3900630a0008b31c85918b6a2a06dd0f41bc547e833118cecca7e22dfa636a` |
| `sft-rl-math-openmathreasoning` | `u102.part0001.jsonl` | 212,095,371 | `caca9a2d8b5d32736d0d96e7b0f48c3aad2fa01a8687a84e322bed5a0235f45e` |
| `sft-rl-math-openmathreasoning` | `u122.part0001.jsonl` | 212,081,328 | `f989ab14fa7b9fee5b0c389ca0f00989bcb17eb654ff2f8d850ade17aede915f` |
| `sft-rl-math-openmathreasoning` | `u117.part0000.jsonl` | 300,009,029 | `0ad4c27fc1e630343b0ec2692b8f1f95a60867ae5ff95b63f0e81816befe2f0e` |
| `sft-rl-math-openmathreasoning` | `u069.part0001.jsonl` | 212,277,181 | `b302371f5780965b4282d8b37dddd36c0b724fad78e8d7d84a656a4467eebc71` |
| `sft-rl-math-openmathreasoning` | `u117.part0001.jsonl` | 211,778,661 | `597eb47ebe76dbf470a1c69179e29ffbaa00ea5fe46543af912cf8a189d0b1e8` |
| `sft-rl-math-openmathreasoning` | `u011.part0000.jsonl` | 300,024,500 | `8cf1cd73672f0ca5bc53f16f8aea0d83dd559096aaf067e5cdaf73c1c57c82f1` |
| `sft-rl-math-openmathreasoning` | `u123.part0000.jsonl` | 300,004,573 | `c8b785398d99334deeaa82ed28e5348fb8ead9baf06e99ad482d78c91204d4dc` |
| `sft-rl-math-openmathreasoning` | `u110.part0000.jsonl` | 300,005,108 | `4bb92009ee5a52523271fb8ff18b8e47e1096f8b1c9322f6dea458ad49701698` |
| `sft-rl-math-openmathreasoning` | `u011.part0001.jsonl` | 212,046,019 | `9c4e47b14143502743b45c597f3be6dd0409df3900e2bfe5986479cadde5bfb0` |
| `sft-rl-math-openmathreasoning` | `u089.part0000.jsonl` | 300,013,231 | `823281a91af7ff9712aa05fd225679f1c229d3bc71a64d435335cbcd5be36c01` |
| `sft-rl-math-openmathreasoning` | `u123.part0001.jsonl` | 211,870,055 | `a3230c8be5c53ba05be8feb1746c96bf383d71e66d437441886a52c447fa46bd` |
| `sft-rl-math-openmathreasoning` | `u110.part0001.jsonl` | 211,807,233 | `9c92c356f9280217f62e160c25f075f58f809f5a404a69398a4e13a01a939ff2` |
| `sft-rl-math-openmathreasoning` | `u089.part0001.jsonl` | 211,610,312 | `d883a55296e6689054c16bdcc0423170377e9e161a82923aaa4ce3f98033c140` |
| `sft-rl-math-openmathreasoning` | `u075.part0000.jsonl` | 300,029,631 | `63d15f074368d2b58b28a6f9c010dd5768083d79f5ea64e73a91c1816db94b00` |
| `sft-rl-math-openmathreasoning` | `u125.part0000.jsonl` | 300,035,789 | `e218b54ea1cbef7c6c95642beb2e498e61c520126804ac19ac3923b0a9e92d07` |
| `sft-rl-math-openmathreasoning` | `u068.part0000.jsonl` | 300,009,822 | `8265fcb2fb35a2747b313496d42bd31829cf9884f6a17b984f23267d7d025912` |
| `sft-rl-math-openmathreasoning` | `u000.part0000.jsonl` | 300,011,879 | `b4eb091ba0fe86cf46f0f7d068420f4db12378c1562e7ea7b64c153d15f6c16c` |
| `sft-rl-math-openmathreasoning` | `u075.part0001.jsonl` | 211,878,970 | `ec3bb1f3cd8d906123b758e609a9118e806e96313deca2f0b735528cba5e3e8d` |
| `sft-rl-math-openmathreasoning` | `u125.part0001.jsonl` | 211,499,339 | `c34a1e697823bb3d0bd179c33d5a742c7cd4f55e87777b38e6558e84af0227b9` |
| `sft-rl-math-openmathreasoning` | `u068.part0001.jsonl` | 211,927,171 | `fde2754201af1062f3aa702757de3d9039fd6ed6c58d43fa8a9da2e292dc12c1` |
| `sft-rl-math-openmathreasoning` | `u000.part0001.jsonl` | 211,228,966 | `de98740cb1a9364e4ca1def0147e5274fd2b63343e6ac8cb03786a88fb2d0704` |
| `sft-rl-math-openmathreasoning` | `u023.part0000.jsonl` | 300,001,421 | `fdfa94442af6d06cc1ef2a8f4f64e400183c6890414d1c58de406aea9bda0fbe` |
| `sft-rl-math-openmathreasoning` | `u066.part0000.jsonl` | 300,014,961 | `80e457ce6472b285821791f2c4d69f52195f64a68dbdf41124afb812767fa966` |
| `sft-rl-math-openmathreasoning` | `u013.part0000.jsonl` | 300,025,929 | `29eae2a9bcebddb7e7c9399d89a71b6f1151e8a1cdf015f7769a26023202a3ba` |
| `sft-rl-math-openmathreasoning` | `u056.part0000.jsonl` | 300,009,910 | `5a07211c8551fc87d710d3d4fb76c7182fc6a4d461111677e8859e4862240073` |
| `sft-rl-math-openmathreasoning` | `u023.part0001.jsonl` | 211,298,612 | `25e720a1e067ee2cc00b4b9e9aa724db05d3c62dee7b1833af0d0992b56f6bf0` |
| `sft-rl-math-openmathreasoning` | `u066.part0001.jsonl` | 211,672,202 | `d01f2564c85ad9ed83befa2ebf257c292f393b2dc3fe85d5c9a21a99ac24a40b` |
| `sft-rl-math-openmathreasoning` | `u013.part0001.jsonl` | 211,381,661 | `a10b3b9ad5e97eb13ba0e638b8cc337efdcdc2bf0d4283b0e98b8a62efb5fef8` |
| `sft-rl-math-openmathreasoning` | `u056.part0001.jsonl` | 211,453,551 | `1f85a7a6f0134b882202a4797db366fa12b9b629f08947aecf49ac0bd5c1a554` |
| `sft-rl-math-openmathreasoning` | `u030.part0000.jsonl` | 300,014,856 | `5e110ce4bd1dade771cdfa7728b550f99792878d822bdb94d360c51db2aebaf0` |
| `sft-rl-math-openmathreasoning` | `u134.part0000.jsonl` | 300,005,610 | `21799c17f3b6efa0f7e46895e05dcee1472bedb188a460ac455f9c5da5987bc1` |
| `sft-rl-math-openmathreasoning` | `u077.part0000.jsonl` | 300,026,638 | `ddafc61ddcae52d4187c49e2ba09cf84142651a4249954a01e685a2f80a7178c` |
| `sft-rl-math-openmathreasoning` | `u059.part0000.jsonl` | 300,012,884 | `002fbf595344686db24b1b24b81a74466ba65ea0a48e24c0265c1c30ce0d4823` |
| `sft-rl-math-openmathreasoning` | `u030.part0001.jsonl` | 211,247,512 | `42c1d386c5ba8e1df62b00c879b2cb784413d41a2a60121107d077881fe3c3c4` |
| `sft-rl-math-openmathreasoning` | `u134.part0001.jsonl` | 211,421,953 | `7bd9116c62c2b5025831d7de63b4d2e570d4b0c2bed6c36596c3ddadf4a875d0` |
| `sft-rl-math-openmathreasoning` | `u077.part0001.jsonl` | 211,520,358 | `26a3df308f53dd18a604e05d0dec3d2d19d30cb21ac8973fbca14401e6c06ee0` |
| `sft-rl-math-openmathreasoning` | `u059.part0001.jsonl` | 211,387,692 | `d6507c46924c857ad9c8970c848afb2c11f63d24b943dd9c97ca4243dab42996` |
| `sft-rl-math-openmathreasoning` | `u012.part0000.jsonl` | 300,009,771 | `0dd60ae60b6768cc696e4c9a3f494556d22cff48d940755ed60b572d89c0c6e4` |
| `sft-rl-math-openmathreasoning` | `u081.part0000.jsonl` | 300,001,801 | `8bfbb09cd5706cefd4706db5d75136b37461a1de9fd736ce65645aedbc65dcb0` |
| `sft-rl-math-openmathreasoning` | `u067.part0000.jsonl` | 300,003,234 | `54bd3e2a68f92ebe931864486d7550764262c58e313a87d0a0ac3f0fd2af108b` |
| `sft-rl-math-openmathreasoning` | `u113.part0000.jsonl` | 300,008,126 | `30ccac06083654497b597b01868c30693530cb6d3d6adf3806206c6bf10a345e` |
| `sft-rl-math-openmathreasoning` | `u012.part0001.jsonl` | 211,296,862 | `ce445bec266b33e5c63203dcef918b9422783ba2508a3e13edcf59b152caf0f6` |
| `sft-rl-math-openmathreasoning` | `u081.part0001.jsonl` | 211,274,776 | `2d30236b601e4ba82f76dc007f690031dc7eae4913c3ab4add00466759d89652` |
| `sft-rl-math-openmathreasoning` | `u067.part0001.jsonl` | 210,343,859 | `c86458d0a5af41b926e167122405457a4c274d142817838e9eec2ad38c1a871a` |
| `sft-rl-math-openmathreasoning` | `u113.part0001.jsonl` | 211,098,680 | `6aff45fd37bbe6c03ad37987ad085a6c80fa6e9b0560fee3131582abd816559f` |
| `sft-rl-math-openmathreasoning` | `u054.part0000.jsonl` | 300,001,573 | `bc3bcefed06e5a89a8c6a950fae654675894347fb674e1f12c7a1a34982596e6` |
| `sft-rl-math-openmathreasoning` | `u004.part0000.jsonl` | 300,000,906 | `5efaa7adf8c4531d8b6c11478b4e1c04022d0dbf095f071dc8481f270b67517d` |
| `sft-rl-math-openmathreasoning` | `u103.part0000.jsonl` | 300,022,532 | `04005f6b9a994204edcb13315db3f12dca52d4f12139d68243a240c929d2eac7` |
| `sft-rl-math-openmathreasoning` | `u009.part0000.jsonl` | 300,023,786 | `c1af1ec080e81d678831880c20f27fa5caee95ac47cd64714fe135db7c64f1fa` |
| `sft-rl-math-openmathreasoning` | `u054.part0001.jsonl` | 211,017,755 | `c9a8c19ee554c4689697536ba18a061ff06f8923d571fbb82181509278cf8092` |
| `sft-rl-math-openmathreasoning` | `u004.part0001.jsonl` | 210,815,407 | `d955e66debc397fb4648f5a20a7f5bd3766513c635e1ec861d2a5f8a7bdca791` |
| `sft-rl-math-openmathreasoning` | `u103.part0001.jsonl` | 210,490,556 | `2385bccbc30c4793660d0151ee273fd4041444cfcbc63a6009fde533eb991428` |
| `sft-rl-math-openmathreasoning` | `u009.part0001.jsonl` | 210,426,066 | `a06d822974c2569c3c80abb6aa15ca074e27c9bf77639a207efa16b10a1be66b` |
| `sft-rl-math-openmathreasoning` | `u021.part0000.jsonl` | 300,012,291 | `afffac21ffe7865a7ca63123234c7123eb2ed5cb0684c2e2ec662b06b1511396` |
| `sft-rl-math-openmathreasoning` | `u105.part0000.jsonl` | 300,008,072 | `129444013c40a964d4cb315f7436dce03d64ac9b69fcee40f8cd4dff391e236e` |
| `sft-rl-math-openmathreasoning` | `u137.part0000.jsonl` | 300,009,241 | `44a7edfce18ef7223b97717b363b074d6caca469251e66232da5884b85d8f36b` |
| `sft-rl-math-openmathreasoning` | `u021.part0001.jsonl` | 211,003,989 | `9ac68435a9eb2b7d2dfa3f77e19e54383442b981511a8dc091a981326773ce38` |
| `sft-rl-math-openmathreasoning` | `u019.part0000.jsonl` | 300,021,704 | `1b9a6dcdb5b69e8a12a2c2a123029d9eca1b4bb319c1d8fb9492259e9f424da1` |
| `sft-rl-math-openmathreasoning` | `u105.part0001.jsonl` | 210,658,199 | `ab8ba986c0467ea07ad9cf255c0ff25edcc6601e9143f616266f20791b113ca9` |
| `sft-rl-math-openmathreasoning` | `u137.part0001.jsonl` | 210,566,630 | `b81b588e1aaa27e9104f5f485c92230554db13d8ccd3c2abc503914d6e76f6a4` |
| `sft-rl-math-openmathreasoning` | `u019.part0001.jsonl` | 210,185,007 | `02472f53da0c3e6bfc3e9e8734075852fd49926a611e3fc12507c4c6536c8806` |
| `sft-rl-math-openmathreasoning` | `u131.part0000.jsonl` | 300,028,913 | `b4b5b85d33b8d5bf27504be6fc68f813f732c5d416d74ee00d1501511561eeb4` |
| `sft-rl-math-openmathreasoning` | `u088.part0000.jsonl` | 300,015,303 | `fcee44051d9e8871a647709f536635688a06b4628e56346cb9b8c54345f2b4c3` |
| `sft-rl-math-openmathreasoning` | `u058.part0000.jsonl` | 300,010,975 | `0e89322f5d54900d18a0643a435a25b1f27ff1353f0832b76fdd3e594f0ce2b5` |
| `sft-rl-math-openmathreasoning` | `u131.part0001.jsonl` | 210,141,381 | `092497cea6b73509b86bd57f038c46f9d67c8a2b5093e9b0e274910e7cf5910d` |
| `sft-rl-math-openmathreasoning` | `u049.part0000.jsonl` | 300,011,478 | `da7f52494324fbca0f305061f732ac44feb3d20c5e062dc45251cf32e5db1f18` |
| `sft-rl-math-openmathreasoning` | `u088.part0001.jsonl` | 209,875,387 | `88e758764e85c5f7bd3ae88eed8d5544d7b83620ed6e99a6d7d6f1f2a337a34c` |
| `sft-rl-math-openmathreasoning` | `u058.part0001.jsonl` | 209,304,725 | `20144d15e00e082517a21acc03e63f3070b84981adb81f5d3ae4f82d21078bbc` |
| `sft-rl-math-openmathreasoning` | `u049.part0001.jsonl` | 207,202,359 | `4be3c207b2c2aae5b32aa0670cb94cc0c4135dcce962972e2a3214dc243e9cea` |
| `sft-salesforce-xlam-60k` | `u000.part0000.jsonl` | 111,560,188 | `79a293c5f4e26f97200cc50559ceb253e9c2846d6fccd6318d412330b3de6b5c` |
| `sft-science-glm51-phd` | `science-glm51-phd.jsonl` | 2,013,871,482 | `88165c31230c1a5efab08882c7c5160ebe032b7b0b1a7e500cbca1e3903aa387` |
| `sft-science-nemotron-science-v2` | `science-nemotron-science-v2.jsonl` | 571,034,022 | `ec5a5bf12503b7e798da641a895ccae1ade0ba3c0e9c31f22d9cf02473d5148b` |
| `sft-science-nemotron-science` | `science-nemotron-science.jsonl` | 1,808,296,419 | `339a9bdf19fc9fcc12124ed9c1ded743b22afe45c818249b028fe293c250ba95` |
| `sft-stem-code-openthoughts3` | `u005.part0000.jsonl` | 179,951,314 | `61b966fb0dcf8c81a40d94f3143371a7543669a38652f1ac0b654bb5202375f8` |
| `sft-stem-code-openthoughts3` | `u002.part0000.jsonl` | 183,522,542 | `02860363d35598f7e4362ed270120dd478dd7fdb5e9c5f5cb8e80b8cdcaabbdc` |
| `sft-stem-code-openthoughts3` | `u003.part0000.jsonl` | 181,978,287 | `77de6fafafd2f2c80e06d33bc5cb41909613d889fed1733688bcfb90cd7356f8` |
| `sft-stem-code-openthoughts3` | `u009.part0000.jsonl` | 183,065,704 | `5f4c0a2f877cc02cb2f7948d7536a8b1aab37973e0b1283b00477fd3bb1a2fd1` |
| `sft-stem-code-openthoughts3` | `u019.part0000.jsonl` | 186,249,245 | `cadbaacb0fb395c668d15c363530154d9c14139db48f2bacb5e1bfe61d7f6ce8` |
| `sft-stem-code-openthoughts3` | `u017.part0000.jsonl` | 187,750,995 | `fa987c85d2b2554911dc08664c2d47bbd15b9651d791a0877ad6572b1a9913f4` |
| `sft-stem-code-openthoughts3` | `u024.part0000.jsonl` | 183,370,418 | `3c063420f17512d9295a412717d6bb90981a1823582373084c578a06052f11b9` |
| `sft-stem-code-openthoughts3` | `u004.part0000.jsonl` | 187,089,142 | `be316d8b23bf4b96511ceda3a6c5ee7ad229d0f2aaa481361cf4807125d88c2b` |
| `sft-stem-code-openthoughts3` | `u015.part0000.jsonl` | 188,079,020 | `e909cf8e6ec1533f14aafa562318348bec90b6977f0902ea795d39f86001f383` |
| `sft-stem-code-openthoughts3` | `u000.part0000.jsonl` | 186,208,977 | `81ed82c8b1b8b21cbb1baee21820b530ff48cb6c9cdb9ec1d63eea825538f07c` |
| `sft-stem-code-openthoughts3` | `u008.part0000.jsonl` | 181,492,005 | `fa77f0161988eacd5ad658902641cebc0f32924b2d95beb252ce3f2102a8d2bf` |
| `sft-stem-code-openthoughts3` | `u010.part0000.jsonl` | 187,829,340 | `64a6876f25baada6739e9b38f1f2aa7dbcf2b81f2199166c85d94fbb0bb6b4d6` |
| `sft-stem-code-openthoughts3` | `u023.part0000.jsonl` | 190,781,933 | `b59992ac57ba6f07948242edcbe741a72d350367f02e592ba93ad4b26eec45c1` |
| `sft-stem-code-openthoughts3` | `u020.part0000.jsonl` | 184,083,248 | `bfe363eda594def72f3903e9a711383c6986531e89c60f85ff55657a22d7d205` |
| `sft-stem-code-openthoughts3` | `u022.part0000.jsonl` | 185,100,592 | `3c9c086f9d302602afcca8c3459cf68dc921f9132094d2ce04168564dfd634a2` |
| `sft-stem-code-openthoughts3` | `u007.part0000.jsonl` | 186,817,149 | `3f3553f6e92bd0cd62b50b73adcb5ae23eb38f6fe242fcf54150623bd9f40b88` |
| `sft-stem-code-openthoughts3` | `u011.part0000.jsonl` | 189,623,793 | `89b629aa0d5dca70e961323ea977c8947f9f647aa5622b3c97cada0d64b68fc4` |
| `sft-stem-code-openthoughts3` | `u013.part0000.jsonl` | 191,184,696 | `5c48fe9a66897bc96488b0d7e33829851ffa06b1ed15339ecd6364ca58866b31` |
| `sft-stem-code-openthoughts3` | `u001.part0000.jsonl` | 187,860,252 | `fc893723343f0cda168add0c7263d681fd7fd8d8d5d1c5e1c72869803000489a` |
| `sft-stem-code-openthoughts3` | `u016.part0000.jsonl` | 182,158,069 | `2939bf5d7a87e9854c3bb2cb417d3faaa231f1233baa71ad5ceaf17903b734b4` |
| `sft-stem-code-openthoughts3` | `u021.part0000.jsonl` | 186,471,804 | `934553e4b07839059c5688da720b61cf4c1c9b1afd361f0e6852452b732acb7c` |
| `sft-stem-code-openthoughts3` | `u014.part0000.jsonl` | 182,324,121 | `15d2f2c135b3d0cd15cb0f7996c6c2827268b8991ee45c4b33eac5033b7ee2ed` |
| `sft-stem-code-openthoughts3` | `u018.part0000.jsonl` | 182,997,142 | `5f03dc8910904343a6f6ed88bf559c04f73b01c57ab720569e27d71b028faee6` |
| `sft-stem-code-openthoughts3` | `u006.part0000.jsonl` | 185,938,272 | `fb248cb1ec0c647d03ecc32a7326de70e3f899aa0d3e53c8ea053c7be35da9c5` |
| `sft-stem-code-openthoughts3` | `u012.part0000.jsonl` | 188,851,693 | `62af1dcf7c27514bfc5f328366643d3dcf4378d11f1847b7d0333a848425cea9` |
| `sft-stem-code-openthoughts3` | `u032.part0000.jsonl` | 142,917,791 | `3bfffd688504e8dff37beb4b50b1456dd5c7be1424cff666b53fdd4584667744` |
| `sft-stem-code-openthoughts3` | `u030.part0000.jsonl` | 146,550,371 | `6261bfaaf9122e754f6f83e93136392b790172bb8b5957d4743226decd1b5c3e` |
| `sft-stem-code-openthoughts3` | `u049.part0000.jsonl` | 147,206,726 | `5d68b73f751ceb0eec0cd6fe3895eb6496bb1611f398299667d42ed59175b653` |
| `sft-stem-code-openthoughts3` | `u086.part0000.jsonl` | 146,309,531 | `a4de4008e45abf95510569d3c369b0159d482ef99cad4f5c56089105641b7c75` |
| `sft-stem-code-openthoughts3` | `u070.part0000.jsonl` | 144,020,843 | `cd2a87abcb3b4642999d77e9972d0ed725fc7d5c32e84132794e7143746ff3d1` |
| `sft-stem-code-openthoughts3` | `u053.part0000.jsonl` | 146,190,775 | `04914dae1561da4367efd11fa56726d1f63d75fcde93685ff509e80c0a9561d9` |
| `sft-stem-code-openthoughts3` | `u060.part0000.jsonl` | 145,007,957 | `cc0acc8186a7e68b2f245c03f4227eee60de1fee0b8a200744edefed7e27a9f3` |
| `sft-stem-code-openthoughts3` | `u085.part0000.jsonl` | 149,315,608 | `4790019c6a72444494b9c603ae1f2b7947a36f8d82dbff7fe85b70dc60e19bfd` |
| `sft-stem-code-openthoughts3` | `u080.part0000.jsonl` | 142,341,269 | `bd0cd7a2cf5ffb49d4e386b0dd1af1cebb6273813f45c21c0f525bbbf56348c9` |
| `sft-stem-code-openthoughts3` | `u043.part0000.jsonl` | 145,461,840 | `03825debb4f72a6e369a15953c53acdde157f145709184d11f1ce4c75f34c26b` |
| `sft-stem-code-openthoughts3` | `u042.part0000.jsonl` | 142,941,074 | `f0a02e5d4b5c2d8e3d7419a17bd65fb19249ee8e1ba54939596ef07391b186a7` |
| `sft-stem-code-openthoughts3` | `u028.part0000.jsonl` | 143,758,302 | `7ed59b0a78cdbcc757b9ff716a65c4eadb6a740e428feb662932e1fb3843c6e4` |
| `sft-stem-code-openthoughts3` | `u069.part0000.jsonl` | 146,814,630 | `fec281f799072719c2111632dcb618c8b4b4f85b828627c6f7dee55a1187760b` |
| `sft-stem-code-openthoughts3` | `u072.part0000.jsonl` | 142,728,739 | `09a2fcaa9dc6d09e9efb6870751cb038b1dc7ea7b8b239aef9ad1edd7e83f05b` |
| `sft-stem-code-openthoughts3` | `u065.part0000.jsonl` | 145,980,918 | `43781127566e1b63183cf3735c19ad2f00072436b8a8d624d70ab1143ffef705` |
| `sft-stem-code-openthoughts3` | `u029.part0000.jsonl` | 145,795,184 | `8512028228f88f079c3e264debc7224e4bea08700cc16b78af1f50e59b2f2561` |
| `sft-stem-code-openthoughts3` | `u089.part0000.jsonl` | 145,203,696 | `1ecaaee1cae0e244dbfbd44fcebebbe9b3ee823f3b70aedf3fbe446ee74f4587` |
| `sft-stem-code-openthoughts3` | `u038.part0000.jsonl` | 143,508,052 | `075c864df24b64235c01a35be11e494dad10df03fc6ab5000d17bec3bb3c35a4` |
| `sft-stem-code-openthoughts3` | `u054.part0000.jsonl` | 145,992,642 | `e06f715134af296891075401d594f003a3ba558a274ed004e22755554d2cfd5f` |
| `sft-stem-code-openthoughts3` | `u103.part0000.jsonl` | 146,563,174 | `4e7168b8f0eba294934b62217bec19f327bcdda5cf8c5cbab305ee5624ac7f70` |
| `sft-stem-code-openthoughts3` | `u082.part0000.jsonl` | 148,487,102 | `4e7bd4e5c9d92bb3f32e7396d2dacb8b14474b85637827cef58af9fbd01e809b` |
| `sft-stem-code-openthoughts3` | `u031.part0000.jsonl` | 145,882,242 | `5a8fa588c1fb1e57944d5d90aa9073decdf73e10c1d4d7a6f747d25272419cc8` |
| `sft-stem-code-openthoughts3` | `u090.part0000.jsonl` | 146,085,575 | `167ecc918bc3d13177ad47b059eb01b7fd4be93932088d90c8fb2ca48d239f0b` |
| `sft-stem-code-openthoughts3` | `u056.part0000.jsonl` | 147,581,393 | `a22c1624147c35b692a534b4f33ff7b38525ef30763ec909d9ccb4af993fd71d` |
| `sft-stem-code-openthoughts3` | `u026.part0000.jsonl` | 141,571,322 | `b48337cd5fa8c34915b96289a2e2eddc2e1eb7ba3c6644f8cd6b573dba06654b` |
| `sft-stem-code-openthoughts3` | `u058.part0000.jsonl` | 143,441,203 | `5d9023e78872a2d6b1cf07aa5f36064698a041090ffaa6044974876404f70d40` |
| `sft-stem-code-openthoughts3` | `u061.part0000.jsonl` | 144,007,123 | `17a6b696aaa2bef4b6ca2105bb9cd81cc835db8a1c92925dc8d383537a00abf1` |
| `sft-stem-code-openthoughts3` | `u095.part0000.jsonl` | 143,050,154 | `059640cd40806b3ea0f904eaa3e10a603bb24394cb121549259f671bb75b2d35` |
| `sft-stem-code-openthoughts3` | `u047.part0000.jsonl` | 145,364,208 | `f8cc96d2682eb6ec74fef413dc9321716cecdbf5f126ca1f1ecf8b1d3a93a9b7` |
| `sft-stem-code-openthoughts3` | `u066.part0000.jsonl` | 148,543,747 | `e93a0eb81429801e516a3fc1536c61e419185a4ef664be39d5cc2ecd94dfbae5` |
| `sft-stem-code-openthoughts3` | `u079.part0000.jsonl` | 148,756,712 | `c2286377d74eed71922168fa3a12d9c4bc89c2db6a0ff3510d28640099e35044` |
| `sft-stem-code-openthoughts3` | `u039.part0000.jsonl` | 143,116,423 | `3e3bc316a4a93a1883a0cddec55bd92afabb23eb54da653cbbc131e612b1aa3d` |
| `sft-stem-code-openthoughts3` | `u037.part0000.jsonl` | 145,809,620 | `30339caab7608f5ef8e346d4eea4c5af5b4d5e9b61d631235e56920b1c6aa243` |
| `sft-stem-code-openthoughts3` | `u035.part0000.jsonl` | 148,152,370 | `1fc0858d7a4537a93c27745841a19854edf04d3f94bb05950bca2e47f0f512bf` |
| `sft-stem-code-openthoughts3` | `u041.part0000.jsonl` | 145,097,828 | `5e8af92cdfb81d53701eb7dc850e4b0136de533a5f8954731735c55fe99c187a` |
| `sft-stem-code-openthoughts3` | `u087.part0000.jsonl` | 148,117,135 | `d7db6887aa8b323513b91c8d6afe58765ac5594d3c4043808effef3e2d9d993d` |
| `sft-stem-code-openthoughts3` | `u096.part0000.jsonl` | 146,191,915 | `ef77a9aff71d0bf9ab4489b5803170c998d67a73778546a13c65625138c428ac` |
| `sft-stem-code-openthoughts3` | `u073.part0000.jsonl` | 149,079,646 | `6cd17509c66b0f5e4e7813ceda69e6d73d18342c5a3f7dfd27b2b25407929c83` |
| `sft-stem-code-openthoughts3` | `u048.part0000.jsonl` | 150,882,141 | `add1fd3dcf49030a05855df54b1aec687132a62505c761de2d18a8735c70d124` |
| `sft-stem-code-openthoughts3` | `u100.part0000.jsonl` | 144,838,601 | `c360b497f2b13a070cd31c645fd68bc0ad835a01f9701d8228a6ca70cd9c306a` |
| `sft-stem-code-openthoughts3` | `u104.part0000.jsonl` | 145,713,729 | `15b0d017f30a9438ae6effccf49a12f41651e6a67a747f20287e3ca7480b4d09` |
| `sft-stem-code-openthoughts3` | `u088.part0000.jsonl` | 144,424,674 | `696756c635fa79725879b5b1f346340515b18a5d649ae3c13790c99c52fc91fe` |
| `sft-stem-code-openthoughts3` | `u025.part0000.jsonl` | 148,920,664 | `d76d9a264339fa84bb70351bff1a61a3e0d654187f14e984b2fc067b9e70a727` |
| `sft-stem-code-openthoughts3` | `u034.part0000.jsonl` | 147,902,122 | `639f7068076b2074212b60b6834cfdfbf723742393646ce610dc6a95c7e1191d` |
| `sft-stem-code-openthoughts3` | `u101.part0000.jsonl` | 148,150,877 | `ed1788508e7e93ef617cbdeb766a033d80c56693a1727e50559da880c3fbcdcd` |
| `sft-stem-code-openthoughts3` | `u083.part0000.jsonl` | 146,703,498 | `224813e8c29f7cdaada90b6a07a6b2c4f9684edf83950fd71370fbfe64593025` |
| `sft-stem-code-openthoughts3` | `u099.part0000.jsonl` | 148,467,191 | `a47a5cdbd829770676754b3c77b5db723d4f0e2a4580e2f7de5d6b5a0f404a7a` |
| `sft-stem-code-openthoughts3` | `u109.part0000.jsonl` | 144,887,109 | `8f42fa43e994426702928ff57b24ca8aa08b0bd4b9e32150e3e1ba720c13426b` |
| `sft-stem-code-openthoughts3` | `u077.part0000.jsonl` | 145,719,987 | `8ed654525e8a6248c16d88db595c27f96b9fa4c957cd58fc01cfbc8b8111efc6` |
| `sft-stem-code-openthoughts3` | `u107.part0000.jsonl` | 145,223,376 | `bf37446cdda455b3cca07fb0d4e234859a4386ab2a8a1e5cfb55b05c6da74416` |
| `sft-stem-code-openthoughts3` | `u055.part0000.jsonl` | 145,108,077 | `d31bd6c52ac22636b4526183cb85843dbb534506f136938920fe5efd88b6ab0a` |
| `sft-stem-code-openthoughts3` | `u068.part0000.jsonl` | 149,435,562 | `7e3ae6a99ba7af79da71fd105841f1e7b8ed3b05766b64ec768358d2babfa7fd` |
| `sft-stem-code-openthoughts3` | `u092.part0000.jsonl` | 145,163,356 | `23a7eaca02e4f93204510e9ef3d8b0929ebcba5fb69d4d57386b23dd9c26df59` |
| `sft-stem-code-openthoughts3` | `u050.part0000.jsonl` | 145,358,101 | `d623770fabbfddd1cead534f751e656af66de5a42001b8b1832b70a2febfb05c` |
| `sft-stem-code-openthoughts3` | `u033.part0000.jsonl` | 143,871,666 | `f5dd773499679c04f8b81e62b86b5914bd8773820925b8f5a8e2132d77d3c840` |
| `sft-stem-code-openthoughts3` | `u052.part0000.jsonl` | 145,180,681 | `6d60a7be42fce5e0e7128c03c684d8cc9ec134095b3df8940bb86ae774903b46` |
| `sft-stem-code-openthoughts3` | `u051.part0000.jsonl` | 142,465,566 | `16685ab74780bdd9bd26c950c797d417fa851746b2c05d1fba1a7d7a2f713339` |
| `sft-stem-code-openthoughts3` | `u091.part0000.jsonl` | 149,785,466 | `5439ebd33999885c571b98503cd82c8d47c4905f8f2a2e7930ad721c907242b8` |
| `sft-stem-code-openthoughts3` | `u064.part0000.jsonl` | 144,842,004 | `70d51f9a08c78eb74aafe0df7491832567e5c87fc78a9a390a5c0f1e283f5ba6` |
| `sft-stem-code-openthoughts3` | `u105.part0000.jsonl` | 148,351,250 | `7903f5d6ddda840dafac799e89714e77a714fbbcc904e2b5b97a2d7163be8c08` |
| `sft-stem-code-openthoughts3` | `u078.part0000.jsonl` | 146,202,972 | `3cddd07f0ca0add87b22deb03875f2df5323f75016dfe677fd530fea42cff415` |
| `sft-stem-code-openthoughts3` | `u076.part0000.jsonl` | 143,506,999 | `402b08e57775b8c4772ab3e00455fd409e85e5fee49409d2949336da24f15111` |
| `sft-stem-code-openthoughts3` | `u036.part0000.jsonl` | 142,303,712 | `fff437d48f5aee93de6163c234d394a484e187cdd09cba6f72f6dbb916806cbc` |
| `sft-stem-code-openthoughts3` | `u098.part0000.jsonl` | 144,269,824 | `01843776659000d648d80f5e3e1c070d94321133ee198d7264acea73af4520a2` |
| `sft-stem-code-openthoughts3` | `u027.part0000.jsonl` | 143,397,985 | `4537d21308eddda29c93dd58d97dc471b9dcfb1963860c8621661c47e9d6bf85` |
| `sft-stem-code-openthoughts3` | `u044.part0000.jsonl` | 146,928,400 | `234552f007144371a52c46cc2564a20ee0463c71646e565df1d80ad23f3321a0` |
| `sft-stem-code-openthoughts3` | `u046.part0000.jsonl` | 145,298,796 | `25eef1f29344df50734ca470dcfc26b9a55e2ebfde26581aba5507686d97fb34` |
| `sft-stem-code-openthoughts3` | `u106.part0000.jsonl` | 148,572,069 | `d1cf9a3fbd8e19f9d421424213bde09a00f0ea9c8a6708613ed6dbc65fc828a2` |
| `sft-stem-code-openthoughts3` | `u075.part0000.jsonl` | 150,485,844 | `d248773eb29b33fbbde059f2a67ed595a1cb09d4934ce0129549767070d60494` |
| `sft-stem-code-openthoughts3` | `u094.part0000.jsonl` | 146,737,416 | `61bc52077cdd7bcae9d2045a0cd55dc92e938f35a9d61959f4ea6c9fa8204160` |
| `sft-stem-code-openthoughts3` | `u057.part0000.jsonl` | 146,083,717 | `bd04a3eb1869a82fa009428ae624fd10190f376a6a0769e365c63de9fd1b37f9` |
| `sft-stem-code-openthoughts3` | `u063.part0000.jsonl` | 150,195,068 | `f49462f53b9ba8a9fa7d5456b4beafc070a82f234df5436d877cc0fd36cbea3b` |
| `sft-stem-code-openthoughts3` | `u081.part0000.jsonl` | 148,205,525 | `3fdacd63c7bb77364405559c449a819b86b18c101207899df11af877ec5370dd` |
| `sft-stem-code-openthoughts3` | `u084.part0000.jsonl` | 143,679,432 | `520315e6b493a2f3fdfc1aac2d22e6448bd1ead6d228d4c70f8c93a7f110a08b` |
| `sft-stem-code-openthoughts3` | `u093.part0000.jsonl` | 146,522,067 | `2dc8ce71ce0d9436e0186f7e3d7668f3c80b06e46f9001c97421dbf972f11702` |
| `sft-stem-code-openthoughts3` | `u040.part0000.jsonl` | 147,530,386 | `7567e02bd6f1d9a2a0f45f5703bbeb34a282e55b0ad4f4b2353f175dcf052b1b` |
| `sft-stem-code-openthoughts3` | `u059.part0000.jsonl` | 147,200,090 | `0d6a54b1153c0b4850f170c6a346b8b2da20dc431fc4d4764bb5a6e1bc02f26a` |
| `sft-stem-code-openthoughts3` | `u067.part0000.jsonl` | 144,575,421 | `8193c45c70f0a02a02a253ab1aaaec33f6a1167db68ceb399d1cf46f7da8386d` |
| `sft-stem-code-openthoughts3` | `u108.part0000.jsonl` | 147,456,157 | `31f005b1a60716067703e893bd7207be4b5474c63167d0433283d891f7d563ad` |
| `sft-stem-code-openthoughts3` | `u045.part0000.jsonl` | 144,841,512 | `44ab5346e065c4f570c8c107aa8c500e332dcc8ac142d6c3551c20ac05c2695c` |
| `sft-stem-code-openthoughts3` | `u097.part0000.jsonl` | 145,779,221 | `a94240998a0410d70163f237747a1d5e95b5469db39edd4185dd2ba9410a4303` |
| `sft-stem-code-openthoughts3` | `u074.part0000.jsonl` | 147,209,452 | `5942c45a3c4d347f162c578ff08987ab0ebf274d91c362eda982706a94ec5689` |
| `sft-stem-code-openthoughts3` | `u062.part0000.jsonl` | 146,165,599 | `ee4f49d702527d42bee61c972f4b45b2cba0447c3a3e7d71765de0fa7f672878` |
| `sft-stem-code-openthoughts3` | `u102.part0000.jsonl` | 143,870,441 | `22eed1e8b58fe1617ef55c42a2eda3bceed77407f1cc8510fac836938ad74107` |
| `sft-stem-code-openthoughts3` | `u071.part0000.jsonl` | 150,395,960 | `07d895bf15a4d25df6a790e88cbc9673ec62e0ff9f2de577b7f37f4080a1924d` |
| `sft-stem-code-openthoughts3` | `u116.part0000.jsonl` | 265,493,867 | `b0e8a91024accce9f72014e9cfc65ee1670ab4989ec886fd8e9272f81df8f67f` |
| `sft-stem-code-openthoughts3` | `u118.part0000.jsonl` | 259,430,397 | `85383c91bc8ff2984d9f6db804cac891eb703cfc1abcedc19e58a1302d5f38da` |
| `sft-stem-code-openthoughts3` | `u113.part0000.jsonl` | 260,321,537 | `2a4a622aa95579f97fcfbf2b35ec4d1a80dc94a86c8ff6b5b722b24570bb3cea` |
| `sft-stem-code-openthoughts3` | `u119.part0000.jsonl` | 259,834,946 | `76e9bd90d56a667268f9d84438f1ad2834886a484ec0debf6ce3b82c49c32b66` |
| `sft-stem-code-openthoughts3` | `u115.part0000.jsonl` | 259,768,184 | `31470c851560af4aecd644d4ff063d74cf3a70266c7a71f06973187153a7f1be` |
| `sft-stem-code-openthoughts3` | `u114.part0000.jsonl` | 260,301,391 | `eccf21971f996eb5c5dbd0c8415b7503bded24af2ef75376d1dae3ae47a11355` |
| `sft-stem-code-openthoughts3` | `u110.part0000.jsonl` | 261,260,853 | `c8db9eeb75c225aa95540610053d24b338bbd0790b7034ab5348e903111d98f2` |
| `sft-stem-code-openthoughts3` | `u111.part0000.jsonl` | 260,187,955 | `c336454ac8fff3ce6e27846f18c63f47d9305641038b7f649db6f57de0b210f3` |
| `sft-stem-code-openthoughts3` | `u117.part0000.jsonl` | 260,902,820 | `4699921b2b4702c625394c65c2753cacc5fe42adb5149391f2427002be2628dd` |
| `sft-stem-code-openthoughts3` | `u112.part0000.jsonl` | 260,814,905 | `66d4fd88dd0cfe1585028292b60ce00b421d7f2ff153e37d073fc5647651339d` |

```
python teams/10-post-training/sft/decontam_run.py --set <set-id> --input <set>.jsonl --out-dir decontam_out
python teams/10-post-training/sft/decontam_report.py --records decontam_out --out decontam_report_30.md --sets <set-id> ...
```

## 7. Sets not in section 1 (9 Nov)

`sft-code-commitpackft` is the python split (56,025 rows, 15 removed). `sft-code-opencodereasoning-2` is all 70 python shards, converted, after joining questions from TACO, APPS, and code_contests by `dataset` + `index` (542,219 rows scanned, 115,067 removed). `sft-math-nemotron-proofs-v3-sft` is the first of 10 parts: 20,023 source rows, 18,266 skipped by `convert.py` because the trace is over the 64k budget, 1,757 checked, 42 removed. An `excluded` set is out of training.

| Set | Status | Why |
|---|---|---|
| `sft-safety-aegis-v1` | text only | Checked 9 Nov on the stored `text` column (11,997 train+test rows, 2 removed). It is not chat: there is no assistant turn, so it is not in the SFT mix as training text. 339 source ids were repeated; the check used one id per row. |
| `sft-safety-indicguard` | excluded | Google Translate and an unnamed generator. |
| `sft-safety-nemotron-guard-v3` | excluded | Google Translate and a Llama jury. |
| `sft-safety-wildjailbreak` | excluded | GPT-4 and GPT-3.5. |
| `sft-safety-nemotron-sft-v2` | excluded | English generator is not named. |
| `sft-code-self-oss-instruct` | excluded | StarCoder2, BigCode OpenRAIL-M. |

## 8. What this check does not cover

- **Benchmarks outside the set.** This fingerprint set holds 20 benchmark entries: `aime_2024`, `aime_2025`, `bfcl_v3`, `codeforces`, `flores200`, `gaia`, `gpqa_diamond`, `gsm8k`, `heldout_g5_v1`, `hle`, `in22_conv`, `in22_gen`, `livecodebench`, `longbench_v2`, `milu`, `mmlu`, `swe_bench_live`, `swe_bench_pro`, `swe_bench_verified`, `terminal_bench_2`.
  It has no entry for HumanEval, HumanEval+, MBPP, MBPP+, ARC-Challenge, ARC-Easy, HellaSwag, TruthfulQA, MMLU-Pro, BBH, MuSR, Belebele, which Team 9's harnesses run (eval firewall, section 5, known gap), so a clean result says nothing about them.
  `sft_mix_proposal.md` section 1 was corrected on 9 Nov: HumanEval, HumanEval+, MBPP, and MBPP+ are not in this fingerprint set.
- **Paraphrase.** The check finds copied runs of words. A reworded or translated item is not found.
- **Other rows of a set.** Only the rows that were run are covered. A set that was sampled (for example the first rows of a split) is not cleared as a whole.
- **Frozen tokenizer.** The check reads the rendered `text`, so it does not depend on the tokenizer. The effort tiers of the rows do, and Team 3 freezes the tokenizer on Sat 14 Nov.
- **A rerun is needed** when Team 9 publishes a new fingerprint set (a different set_sha256), and for any set whose rows change.

