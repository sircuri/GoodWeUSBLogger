set -ex
# SET THE FOLLOWING VARIABLES
# image name
IMAGE=GoodWeUSBLogger
MASTER=1

BASEVERSION="$(date +'%Y.%m')"
VERSION="${BASEVERSION}.${CI_PIPELINE_ID}"

if [ $CI_COMMIT_REF_SLUG != "master" ]; then
    VERSION="${VERSION}-B${CI_COMMIT_REF_SLUG}"
    MASTER=0
fi

echo "version: $VERSION"

echo "Build ${IMAGE}"
mkdir -p out
package="${IMAGE}.${VERSION}.tar.gz"
tar -cvzf "out/${package}" --exclude-from=./ci/exclude.tar ./
