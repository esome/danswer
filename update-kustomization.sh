#!/bin/bash

set -eo pipefail

cat >deployment/kubernetes/kustomization.yaml <<-EOT
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
EOT

for path in deployment/kubernetes/*.yaml; do
	file="${path##*/}"
	case "$file" in
		secrets.yaml|kustomization.yaml) continue;;
	esac
	printf -- '- %s\n' "$file" >>deployment/kubernetes/kustomization.yaml
done
