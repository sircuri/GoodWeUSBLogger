set -ex
# SET THE FOLLOWING VARIABLES
# docker hub username
USERNAME=domotica
# image name
IMAGE=GoodWeUSBLogger
MASTER=1

BASEVERSION="$(cat VERSION)"
VERSION="${BASEVERSION}.${CI_PIPELINE_ID}"

if [ $CI_COMMIT_REF_SLUG != "master" ]; then
    VERSION="${VERSION}-B${CI_COMMIT_REF_SLUG}"
    MASTER=0
fi

echo "version: $VERSION"

echo "Build ${IMAGE}"
mkdir -p out
package="${IMAGE}.${VERSION}.tar.gz"
tar -cvzf "out/${package}" --exclude="./ci" --exclude="Dockerfile" --exclude="./out" --exclude="./.git*" ./

echo "Push ${IMAGE} to Octopus Deploy Repository"
curl -X POST ${OCTOPUS_DEPLOY_URL}api/packages/raw?replace=true -H "X-Octopus-ApiKey: ${OCTOPUS_API_KEY}" -F "file=@\"out/${package}\";filename=\"${package}\";type=application/zip"

echo "Create Octopus Release"
docker run --rm sircuri/octo create-release --project ${IMAGE} --version ${VERSION} --package "Upload package":${VERSION} --package "Stop services":${VERSION} --package "Install dependencies":${VERSION} --package "Setup application":${VERSION} --package "Setup Restart Daemon":${VERSION} --server ${OCTOPUS_DEPLOY_URL} --apiKey ${OCTOPUS_API_KEY}
