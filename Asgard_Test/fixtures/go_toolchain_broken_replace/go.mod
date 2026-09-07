module go_toolchain_broken_replace

go 1.21

require example.com/asguardian-fixture-missing-dep v0.0.0

replace example.com/asguardian-fixture-missing-dep => ../does-not-exist-on-disk/asguardian-fixture-missing-dep
