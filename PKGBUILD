# Maintainer: Meepaw <git@github.com:Me3paw/VPN-gate-CLI.git>
pkgname=vpngate-cli
pkgver=1.0.0
pkgrel=1
pkgdesc="A lightweight CLI for VPN Gate using NetworkManager with legacy OpenSSL support"
arch=('any')
url="https://github.com/Me3paw/VPN-gate-CLI"
license=('MIT')
depends=('python' 'python-requests' 'networkmanager' 'networkmanager-openvpn')
source=("vpngate-cli.py" "LICENSE")
sha256sums=('SKIP' 'SKIP')

package() {
    # Install the script
    install -Dm755 "${srcdir}/vpngate-cli.py" "${pkgdir}/usr/bin/vpngate"
    
    # Install the license
    install -Dm644 "${srcdir}/LICENSE" "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
}
