#!/bin/bash
RED="\033[0;31m"
NC="\033[0m"

prompt() {
  read -e -p "$1 [$2]: " var
  echo ${var:-$2}
}

export DOCKERHOST=$(docker-machine ip vmw)
export PYPI_SERVER_HOST=${PYPI_SERVER_HOST:-$(prompt "PyPI server host" "$DOCKERHOST")}
export PYPI_SERVER_SCHEME=${PYPI_SERVER_SCHEME:-$(prompt "PyPI server scheme" "http://")}
export PYPI_SERVER_PORT=${PYPI_SERVER_PORT:-$(prompt "PyPI server scheme" "8080")}
type=${BASH_ARGV[0]:-dev}

echo -e "${RED}Building ${type} environment...${NC}"
docker-compose -f "layouts/${type}.yml" build --no-cache
docker-compose -f "layouts/${type}.yml" up -d 
