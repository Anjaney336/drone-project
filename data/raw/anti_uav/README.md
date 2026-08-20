# Anti-UAV300 acquisition status

Source: https://github.com/ZhaoJ9014/Anti-UAV

The official 5.6 GB RGB/thermal archive transfer was initiated through the browser on 2026-08-20 but did not complete in the controlled environment. No partial archive is treated as data, and no Anti-UAV metric is reported. Before use:

1. complete the official archive transfer;
2. record archive byte size and SHA-256;
3. review dataset terms separately from the repository's MIT code license;
4. inspect sequences, annotations, splits, and corrupt files;
5. register the verified values in `data/manifests/datasets.yaml`;
6. run a dedicated detector/tracker evaluation without mixing its metrics with navigation simulation.
