# Maintainer: Meepaw <git@github.com:Me3paw/VPN-gate-CLI.git>
pkgname=vpngate-cli
pkgver=1.1.0
pkgrel=1
pkgdesc="A lightweight CLI and GUI for VPN Gate using NetworkManager with legacy OpenSSL support"
arch=('any')
url="https://github.com/Me3paw/VPN-gate-client"
license=('MIT')
depends=('python' 'python-requests' 'python-pyqt6' 'networkmanager' 'networkmanager-openvpn' 'hicolor-icon-theme')
source=("vpngate_cli.py" "vpngate-gui.py" "vpngate_core.py" "256.png" "64.png" "32.png" "vpngate-gui.desktop" "LICENSE")
sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP')

package() {
    # Install the scripts
    install -Dm755 "${srcdir}/vpngate_cli.py" "${pkgdir}/usr/share/${pkgname}/vpngate_cli.py"
    install -Dm755 "${srcdir}/vpngate-gui.py" "${pkgdir}/usr/share/${pkgname}/vpngate-gui.py"
    install -Dm644 "${srcdir}/vpngate_core.py" "${pkgdir}/usr/share/${pkgname}/vpngate_core.py"
    
    # Install icons
    install -Dm644 "${srcdir}/256.png" "${pkgdir}/usr/share/${pkgname}/256.png"
    install -Dm644 "${srcdir}/64.png" "${pkgdir}/usr/share/${pkgname}/64.png"
    install -Dm644 "${srcdir}/32.png" "${pkgdir}/usr/share/${pkgname}/32.png"
    
    # Create symlinks
    mkdir -p "${pkgdir}/usr/bin"
    ln -s "/usr/share/${pkgname}/vpngate_cli.py" "${pkgdir}/usr/bin/vpngate"
    ln -s "/usr/share/${pkgname}/vpngate-gui.py" "${pkgdir}/usr/bin/vpngate-gui"
    
    # Install desktop file
    install -Dm644 "${srcdir}/vpngate-gui.desktop" "${pkgdir}/usr/share/applications/vpngate-gui.desktop"
    
    # Install the license
    install -Dm644 "${srcdir}/LICENSE" "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
}
