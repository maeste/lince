;; Minimal stub of the Zellij host interface, for running the plugin's unit
;; tests under wasmtime (the real functions only exist inside the Zellij
;; runtime). Unit tests exercise pure logic and never reach a host call; the
;; no-op body satisfies the import at instantiation time.
;;
;; Used by tests/run-plugin-tests.sh:
;;   wasmtime run --preload zellij=tests/zellij-host-stub.wat <test>.wasm
(module
  (func (export "host_run_plugin_command"))
)
