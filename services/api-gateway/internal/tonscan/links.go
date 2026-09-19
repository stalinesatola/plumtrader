// Package tonscan builds deep-links into the Tonscan block explorer so the
// mini app and bot can let users verify contracts and transactions
// independently of PlumTrader's own data.
package tonscan

import "fmt"

const baseURL = "https://tonscan.org"

func JettonURL(address string) string {
	return fmt.Sprintf("%s/jetton/%s", baseURL, address)
}

func TransactionURL(hash string) string {
	return fmt.Sprintf("%s/tx/%s", baseURL, hash)
}

func AddressURL(address string) string {
	return fmt.Sprintf("%s/address/%s", baseURL, address)
}
