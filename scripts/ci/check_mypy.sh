set -eo pipefail

# tput는 non-TTY 환경에서 실패할 수 있음
COLOR_GREEN=$(tput setaf 2 2>/dev/null || echo "")
COLOR_BLUE=$(tput setaf 4 2>/dev/null || echo "")
COLOR_RED=$(tput setaf 1 2>/dev/null || echo "")
COLOR_NC=$(tput sgr0 2>/dev/null || echo "")

cd "$(dirname "$0")/../.."

echo "${COLOR_BLUE}Run Mypy${COLOR_NC}"
if ! uv run mypy . ; then
  echo ""
  echo "${COLOR_RED}✖ Mypy found issues.${COLOR_NC}"
  echo "${COLOR_RED}→ Please fix the issues above manually and re-run the command.${COLOR_NC}"
  exit 1
fi

echo "${COLOR_GREEN}Successfully Ended.${COLOR_NC}"
