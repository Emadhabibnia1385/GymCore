#!/usr/bin/env bash
# ============================================================================
# GymCore management menu.
#
# Run it directly on the server (no clone needed):
#   sudo bash <(curl -fsSL https://raw.githubusercontent.com/Emadhabibnia1385/GymCore/main/gymcore.sh)
#
# After installing once, just type:  sudo gymcore
#
# Menu: install · edit tokens/.env · update from GitHub · status · start ·
# stop · restart · logs · uninstall.  Touches ONLY GymCore's own services.
# ============================================================================

REPO_URL="https://github.com/Emadhabibnia1385/GymCore.git"
RAW_MENU_URL="https://raw.githubusercontent.com/Emadhabibnia1385/GymCore/main/gymcore.sh"
SRC_DIR="/opt/gymcore-src"          # cloned source
APP_DIR="/opt/gymcore"              # installed application
ENV_FILE="$APP_DIR/.env"
SELF_BIN="/usr/local/bin/gymcore"
SERVICES=(gymcore-api gymcore-telegram gymcore-bale gymcore-worker)

G='\033[0;32m'; Y='\033[0;33m'; R='\033[0;31m'; C='\033[0;36m'; N='\033[0m'
msg()  { printf "${G}%s${N}\n" "$1"; }
warn() { printf "${Y}%s${N}\n" "$1"; }
err()  { printf "${R}%s${N}\n" "$1" >&2; }
pause(){ read -rp "برای بازگشت به منو Enter بزن..." _ || true; }

require_root() { [[ $EUID -eq 0 ]] || { err "با دسترسی روت اجرا کن:  sudo gymcore"; exit 1; }; }

ensure_deps() {
  command -v git  >/dev/null 2>&1 || { apt-get update -y && apt-get install -y git; }
  command -v curl >/dev/null 2>&1 || { apt-get update -y && apt-get install -y curl; }
}

clone_or_pull() {
  ensure_deps
  if [[ -d "$SRC_DIR/.git" ]]; then
    msg "==> دریافت آخرین تغییرات از گیت‌هاب..."
    git -C "$SRC_DIR" fetch --depth 1 origin main
    git -C "$SRC_DIR" reset --hard origin/main
  else
    msg "==> کلون کردن مخزن..."
    rm -rf "$SRC_DIR"
    git clone --depth 1 "$REPO_URL" "$SRC_DIR"
  fi
}

install_self() {
  # Make the `gymcore` command available for next time.
  if [[ -f "$SRC_DIR/gymcore.sh" ]]; then
    install -m 0755 "$SRC_DIR/gymcore.sh" "$SELF_BIN" 2>/dev/null || true
  else
    curl -fsSL "$RAW_MENU_URL" -o "$SELF_BIN" 2>/dev/null && chmod +x "$SELF_BIN" || true
  fi
}

svc_installed() { systemctl list-unit-files 2>/dev/null | grep -q "^$1.service"; }
active_services() { for s in "${SERVICES[@]}"; do svc_installed "$s" && echo "$s"; done; }

# --- menu actions -----------------------------------------------------------

action_install() {
  require_root
  clone_or_pull
  install_self
  msg "==> اجرای نصب (وسط کار برای پر کردن توکن‌ها ویرایشگر باز می‌شود)..."
  bash "$SRC_DIR/install.sh"
  msg ""
  msg "نصب کامل شد ✅  دفعه بعد فقط این را بزن:  sudo gymcore"
  pause
}

action_update() {
  require_root
  [[ -d "$APP_DIR" ]] || { err "هنوز نصب نشده. اول گزینه ۱ (نصب)."; pause; return; }
  clone_or_pull
  install_self
  msg "==> بازنصب کد جدید (‏.env و دیتابیس دست‌نخورده می‌مانند)..."
  bash "$SRC_DIR/install.sh"
  msg "بروزرسانی انجام شد ✅"
  pause
}

action_env() {
  require_root
  [[ -f "$ENV_FILE" ]] || { err "فایل $ENV_FILE پیدا نشد. اول گزینه ۱ (نصب)."; pause; return; }
  "${EDITOR:-nano}" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  read -rp "سرویس‌ها ری‌استارت شوند تا تغییرات اعمال شود؟ [Y/n] " a || true
  if [[ ! "${a:-Y}" =~ ^[Nn]$ ]]; then
    for s in $(active_services); do systemctl restart "$s" || true; done
    msg "اعمال شد ✅"
  fi
  pause
}

action_status() {
  local found=0
  for s in $(active_services); do
    found=1
    systemctl --no-pager --lines=0 status "$s" || true
    echo ""
  done
  [[ "$found" -eq 1 ]] || warn "هیچ سرویسی نصب نشده. اول گزینه ۱ (نصب)."
  pause
}

action_start()   { require_root; for s in $(active_services); do systemctl start   "$s" || true; done; msg "شروع شد ✅";     pause; }
action_stop()    { require_root; for s in $(active_services); do systemctl stop    "$s" || true; done; msg "متوقف شد ⏹";     pause; }
action_restart() { require_root; for s in $(active_services); do systemctl restart "$s" || true; done; msg "ری‌استارت شد 🔄"; pause; }

action_logs() {
  echo "کدام سرویس؟   1) تلگرام   2) بله   3) worker   4) api   (برای خروج از لاگ: Ctrl+C)"
  read -rp "> " l || true
  case "$l" in
    1) journalctl -u gymcore-telegram -n 100 -f || true ;;
    2) journalctl -u gymcore-bale     -n 100 -f || true ;;
    3) journalctl -u gymcore-worker   -n 100 -f || true ;;
    4) journalctl -u gymcore-api      -n 100 -f || true ;;
    *) warn "نامعتبر" ;;
  esac
}

action_uninstall() {
  require_root
  read -rp "سرویس‌های GymCore حذف شوند؟ [yes/no] " c || true
  [[ "$c" == "yes" ]] || { warn "لغو شد."; pause; return; }
  for s in "${SERVICES[@]}"; do
    systemctl disable --now "$s" 2>/dev/null || true
    rm -f "/etc/systemd/system/$s.service"
  done
  systemctl daemon-reload
  read -rp "پوشه برنامه و دیتابیس ($APP_DIR) هم پاک شود؟ [yes/no] " d || true
  if [[ "$d" == "yes" ]]; then
    rm -rf "$APP_DIR" "$SRC_DIR"
    msg "همه‌چیز حذف شد."
  else
    warn "سرویس‌ها حذف شدند؛ داده‌ها در $APP_DIR باقی ماند."
  fi
  pause
}

menu() {
  while true; do
    clear 2>/dev/null || true
    printf "${C}==================== GymCore ====================${N}\n"
    echo "  1) نصب                         (Install)"
    echo "  2) تنظیم/ویرایش توکن‌ها و .env   (Edit .env)"
    echo "  3) بروزرسانی از گیت‌هاب          (Update)"
    echo "  4) وضعیت سرویس‌ها               (Status)"
    echo "  5) شروع                        (Start)"
    echo "  6) توقف                        (Stop)"
    echo "  7) ری‌استارت                    (Restart)"
    echo "  8) لاگ زنده                     (Logs)"
    echo "  9) حذف                         (Uninstall)"
    echo "  0) خروج                        (Exit)"
    printf "${C}================================================${N}\n"
    read -rp "انتخاب: " choice || exit 0
    case "$choice" in
      1) action_install ;;
      2) action_env ;;
      3) action_update ;;
      4) action_status ;;
      5) action_start ;;
      6) action_stop ;;
      7) action_restart ;;
      8) action_logs ;;
      9) action_uninstall ;;
      0) exit 0 ;;
      *) warn "گزینه نامعتبر"; sleep 1 ;;
    esac
  done
}

require_root
menu
