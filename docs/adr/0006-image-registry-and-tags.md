# ADR-0006: Publish the images on Docker Hub, tagged by date and commit, for amd64 and arm64

- **Status:** accepted
- **Date:** 2026-11-06
- **Author:** Jane Galthie
- **Lesson:** L06

## Context

Step 6 packages the two jobs: the ingestion image (the extractor and the
clickstream consumer) and the dbt runner. They need a registry, a tag scheme
and a retention policy that is executed, not only written.

| Fact | Figure | Source |
|---|---|---|
| Image sizes, compressed, per platform | ingestion about 180 MB, dbt about 285 MB | Registry listing, 6 November |
| Our Macs are arm64, much of the cohort is not | An image built on a Mac runs on arm64 only, unless built for both | `docker push` warning, 6 November |
| Artifact Registry, our own repository | Refused: `artifactregistry.repositories.create` denied | 6 November |
| Artifact Registry, the course's `dataeng` repository | Push works, delete does not: `artifactregistry.tags.delete` denied | 6 November |
| Other groups in `dataeng` | Untagged versions and a retention probe left behind | Registry listing, 6 November |
| Docker Hub, our own account | Push and delete both work | 6 November, below |

## Options considered

| Option | For | Against |
|---|---|---|
| **Artifact Registry, course repository** | Private to the course project, same region as our data, no new account | We cannot delete, so retention cannot be executed. A shared repository: every group can write next to every other |
| **Docker Hub, our own repositories** | We own them: push, delete and retention are ours to run | Public on the free plan. One more account and token |

For the tag: **date and commit** (`YYYYMMDD-<short SHA>`), **date and step**
(`20261106T-step6-01`, as another group does), or **commit only**.

## Criteria

- **Retention must be executed**, by us, with its command and output. This
  rules out the course repository.
- **Nothing private in a public image:** the images hold only code that is
  already public on GitHub. `.dockerignore` keeps `.env`, keys, the legacy
  CSV and local data out, and credentials are mounted read-only at run time.
- **A tag names one build, and says which code:** the commit SHA links the
  image to the exact source, the date sorts the tags.
- **It runs on any machine of the course:** amd64 and arm64.

## Decision

**Publish on Docker Hub,** as `docker.io/jgalthie/group4-ingestion` and
`docker.io/jgalthie/group4-transform`. **Tag every image `YYYYMMDD-<short SHA>`** of the
commit it was built from, from a clean working tree, and never `latest`.
**Build for `linux/amd64` and `linux/arm64`** with `docker buildx`.

**Retention:** keep the tag the DAG uses, the one before it, and every tag
younger than 30 days. Delete every other tag, by its full name, never with a
wildcard. The first images are `20261106-0e8643a`, digests `sha256:a26d2977...`
(ingestion) and `sha256:dcefad2f...` (dbt).

## Retention, executed

A probe image, `docker.io/jgalthie/group4-retention-probe:20261106-probe`, was pushed and
then deleted through the Docker Hub API. The API's tag count stayed at 1 with
an empty list, so the deletion was checked from the registry itself:

```
Fri Nov  6 15:08:16 UTC 2026
$ curl -X DELETE https://hub.docker.com/v2/repositories/jgalthie/group4-retention-probe/tags/20261106-probe
HTTP 204
$ tags left in jgalthie/group4-retention-probe
count: 1 []
Fri Nov  6 15:09:50 UTC 2026
$ tags left in jgalthie/group4-retention-probe, one minute later
count: 1 []
Fri Nov  6 15:10:25 UTC 2026
$ docker buildx imagetools inspect docker.io/jgalthie/group4-retention-probe:20261106-probe
ERROR: docker.io/jgalthie/group4-retention-probe:20261106-probe: not found
```

The same deletion on Artifact Registry was refused, which is why the images
moved:

```
Fri Nov  6 14:36:57 UTC 2026
$ gcloud artifacts docker images delete europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group4-retention-probe:20261106-probe --delete-tags --quiet
Digests:
- europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group4-retention-probe@sha256:d82c2ab94640ded77cf76514ce6a84870761105058a4a9e51b05a8a79be97a6c

Tags:
- europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group4-retention-probe:20261106-probe
ERROR: (gcloud.artifacts.docker.images.delete) PERMISSION_DENIED: Permission 'artifactregistry.tags.delete' denied on resource '//artifactregistry.googleapis.com/projects/data-engineering-i1/locations/europe-west1/repositories/dataeng/packages/group4-retention-probe/tags/20261106-probe' (or it may not exist). Remediate access with this Troubleshooter URL or share it with your administrator - https://console.cloud.google.com/iam-admin/troubleshooter/summary;errorId=CiQwMWExYjE0YS05OTNhLTdiMzEtOWJiMi1mY2E3OWRhYzI3ZjASfHByb2plY3RzL2RhdGEtZW5naW5lZXJpbmctaTEvbG9jYXRpb25zL2V1cm9wZS13ZXN0MS9yZXBvc2l0b3JpZXMvZGF0YWVuZy9wYWNrYWdlcy9ncm91cDQtcmV0ZW50aW9uLXByb2JlL3RhZ3MvMjAyNjExMDYtcHJvYmU%3D . This command is authenticated as jgalthie@albertschool.com which is the active account specified by the [core/account] property.
- '@type': type.googleapis.com/google.rpc.ErrorInfo
  domain: artifactregistry.googleapis.com
  metadata:
    error_info_id: CiQwMWExYjE0YS05OTNhLTdiMzEtOWJiMi1mY2E3OWRhYzI3ZjASfHByb2plY3RzL2RhdGEtZW5naW5lZXJpbmctaTEvbG9jYXRpb25zL2V1cm9wZS13ZXN0MS9yZXBvc2l0b3JpZXMvZGF0YWVuZy9wYWNrYWdlcy9ncm91cDQtcmV0ZW50aW9uLXByb2JlL3RhZ3MvMjAyNjExMDYtcHJvYmU=
    permission: artifactregistry.tags.delete
    resource: projects/data-engineering-i1/locations/europe-west1/repositories/dataeng/packages/group4-retention-probe/tags/20261106-probe
    troubleshooter_url: https://console.cloud.google.com/iam-admin/troubleshooter/summary;errorId=CiQwMWExYjE0YS05OTNhLTdiMzEtOWJiMi1mY2E3OWRhYzI3ZjASfHByb2plY3RzL2RhdGEtZW5naW5lZXJpbmctaTEvbG9jYXRpb25zL2V1cm9wZS13ZXN0MS9yZXBvc2l0b3JpZXMvZGF0YWVuZy9wYWNrYWdlcy9ncm91cDQtcmV0ZW50aW9uLXByb2JlL3RhZ3MvMjAyNjExMDYtcHJvYmU%3D
  reason: IAM_PERMISSION_DENIED
$ gcloud artifacts docker images list europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group4-retention-probe --include-tags
Listing items under project data-engineering-i1, location europe-west1, repository dataeng.

IMAGE                                                                           DIGEST                                                                   TAGS            CREATE_TIME          UPDATE_TIME          SIZE
europe-west1-docker.pkg.dev/data-engineering-i1/dataeng/group4-retention-probe  sha256:d82c2ab94640ded77cf76514ce6a84870761105058a4a9e51b05a8a79be97a6c  20261106-probe  2026-11-06T13:59:54  2026-11-06T13:59:54  1901250
```

## Consequences

- **Easier:** anyone can pull an image by its tag, on any machine, and run
  the job it holds. Rolling back is pointing the DAG at the previous tag.
- **Harder:** the repositories belong to Jane's Docker Hub account, and only
  her access token can push and delete. If she is unavailable, nobody can
  publish. The token (read, write, delete) is never written to a file; she
  can revoke it from Docker Hub's settings.
- **Also in the course's `dataeng` repository:** every version is pushed
  there too, as `group4-ingestion` and `group4-transform` with the same tag,
  so the teaching team can see it. The pipeline pulls from Docker Hub only.
  We cannot delete in `dataeng`, so retention does not run there: every
  version stays, and so does the probe `group4-retention-probe`.
- **What would change this decision:** delete rights on a course repository
  would bring the images back to a private registry next to our data. A
  group organisation on Docker Hub would remove the single owner.
