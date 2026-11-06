# Reproducing a job from its image

The step 6 check: run a job from the published image, delete the image, pull it
again by its tag, run the job again, and compare the outputs and the two image
digests. Done by Jane on 6 November 2026, on her Mac, against the local
`albert-marketplace` stack.

The job is the extractor, on the `product` table, written to a local folder so
that nothing in the bucket changes:

    docker run --rm --network albert-marketplace_default \
      -e DATABASE_URL=postgresql://postgres:postgres@db:5432/marketplace \
      -e TABLE=product -e OUT=/data -v <folder>:/data \
      docker.io/jgalthie/group4-ingestion:20261106-0e8643a

## Result

| Check | Run 1 | Run 2 |
|---|---|---|
| Image digest | `sha256:a26d2977...` | the same |
| Rows written | 42,858 | 42,858 |
| Output file | `ae04f788...` | `fed4a2b8...` |

**The image is the same, and so is the code that ran.** The two files differ
because the source moved between the runs: 19 of the 42,858 products changed,
in the column `qty` only, always downwards. That is stock going down as the
load generator places orders. Every other column of every row is equal.

An earlier run of the same build, the same day, from Artifact Registry
(digest `sha256:d4c95590...`), wrote two files with the same SHA-256,
`8aeb48e1...`: no order fell between those two runs.

## Transcript, Docker Hub

```
Fri Nov  6 15:11:09 UTC 2026
docker.io/jgalthie/group4-ingestion:20261106-0e8643a
digest 1: jgalthie/group4-ingestion@sha256:a26d29778cfbfa7eee4b1b6144efe8ae233d71d072a59209e659671e68df8f42
  wrote   42858 rows  /data/product/part-0.parquet
product: 42858 rows, full, 1.5 s
Untagged: jgalthie/group4-ingestion:20261106-0e8643a
Deleted: sha256:a26d29778cfbfa7eee4b1b6144efe8ae233d71d072a59209e659671e68df8f42
docker.io/jgalthie/group4-ingestion:20261106-0e8643a
digest 2: jgalthie/group4-ingestion@sha256:a26d29778cfbfa7eee4b1b6144efe8ae233d71d072a59209e659671e68df8f42
  wrote   42858 rows  /data/product/part-0.parquet
product: 42858 rows, full, 0.9 s
ae04f788d859266bfeb6505ed74c34e57aba735e7e6bc15135eb4a72a378b2a0  /tmp/step6/run1/product/part-0.parquet
fed4a2b8cd993d25948b68c96c7b42c6516a9e7c4c6a72fe44a189cff283da7d  /tmp/step6/run2/product/part-0.parquet
same rows: True | same columns: True
rows that differ: 19 | columns that differ: ['qty']
```

## Transcript, Artifact Registry, bit-identical files

```
Fri Nov  6 14:36:00 UTC 2026
europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group4-ingestion:20261106-0e8643a
digest 1: europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group4-ingestion@sha256:d4c9559078aa4b4a42e6a11cfe7a218222fc054009fd03e8af4ecda2c4d37b46
  wrote   42858 rows  /data/product/part-0.parquet
product: 42858 rows, full, 1.6 s
Untagged: europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group4-ingestion:20261106-0e8643a
Deleted: sha256:d4c9559078aa4b4a42e6a11cfe7a218222fc054009fd03e8af4ecda2c4d37b46
europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group4-ingestion:20261106-0e8643a
digest 2: europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group4-ingestion@sha256:d4c9559078aa4b4a42e6a11cfe7a218222fc054009fd03e8af4ecda2c4d37b46
  wrote   42858 rows  /data/product/part-0.parquet
product: 42858 rows, full, 1.0 s
8aeb48e13df0e224aa3a9c713e11ad0066bb37c8d1e4c992e0c42c16a2e92ce1  /tmp/step6/run1/product/part-0.parquet
8aeb48e13df0e224aa3a9c713e11ad0066bb37c8d1e4c992e0c42c16a2e92ce1  /tmp/step6/run2/product/part-0.parquet
```

The images now live on Docker Hub, see
[ADR 0006](adr/0006-image-registry-and-tags.md).
