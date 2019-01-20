set -ex

# SET THE FOLLOWING VARIABLES

# MQTT_Port
# MQTT_Server
# MQTT_Topic
# MQTT_ClientId__g
# MQTT_ClientId__z
# Inverter_DiscoveryInterval
# Inverter_LogFile
# Inverter_LogLevel
# Inverter_ModelId
# Inverter_PollInterval
# Inverter_StatemachineTimeout
# Inverter_VendorId
# SSH_PRIVATE_KEY__g
# SSH_PRIVATE_KEY__z

BASEVERSION="$(date +'%Y.%m')"
VERSION="${BASEVERSION}.${CI_PIPELINE_ID}"
if [ $CI_COMMIT_REF_SLUG != "master" ]; then
    VERSION="${VERSION}-B${CI_COMMIT_REF_SLUG}"
fi

IMAGE=GoodWeUSBLogger
package="${IMAGE}.${VERSION}.tar.gz"

# Setup OpenSSH agent
apk add --update openssh-client
apk add --update libintl
apk add --virtual build_deps gettext
cp /usr/bin/envsubst /usr/local/bin/envsubst
apk del build_deps

eval $(ssh-agent -s)

echo "$SSH_PRIVATE_KEY__g" | tr -d '\r' | ssh-add - > /dev/null
echo "$SSH_PRIVATE_KEY__z" | tr -d '\r' | ssh-add - > /dev/null

mkdir -p ~/.ssh
chmod 700 ~/.ssh

# extract config file from package
cd out
tar -xvzf $package ./etc/goodwe.conf

for target in ${TARGETS//;/ } ; do

    ENV_VAR_MQTT_ClientId="MQTT_ClientId__${target}"
    ENV_VAR_MQTT_ClientId_EVAL=$(eval echo \$${ENV_VAR_MQTT_ClientId})

    ENV_VAR_TARGET_IP="TARGET_IP__${target}"
    ENV_VAR_TARGET_IP_EVAL=$(eval echo \$${ENV_VAR_TARGET_IP})

    # replace vars in config file
    MQTT_ClientId=$ENV_VAR_MQTT_ClientId_EVAL
    export MQTT_ClientId

    envsubst < "etc/goodwe.conf" > "etc/goodwe.conf.replaced"
    cat etc/goodwe.conf.replaced

    ssh -o StrictHostKeyChecking=no pi@$ENV_VAR_TARGET_IP_EVAL "mkdir -p ~/.deploy/${VERSION}"
    scp $package pi@$ENV_VAR_TARGET_IP_EVAL:~/.deploy/${VERSION}/${IMAGE}.tar.gz
    scp etc/goodwe.conf.replaced pi@$ENV_VAR_TARGET_IP_EVAL:~/.deploy/${VERSION}/goodwe.conf.replaced

    ssh pi@$ENV_VAR_TARGET_IP_EVAL "cd ~/.deploy/${VERSION} && tar -xvzf GoodWeUSBLogger.tar.gz && rm GoodWeUSBLogger.tar.gz && /bin/sh ./deploy/stop-services.sh && /bin/sh ./deploy/install-dependencies.sh && /bin/sh ./deploy/setup-application.sh && /bin/sh ./deploy/setup-restartd.sh"

done
