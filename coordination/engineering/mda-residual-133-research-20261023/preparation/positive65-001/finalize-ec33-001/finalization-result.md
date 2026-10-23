# Current-main finalization result

This records stock finalization of the existing 65-cell MDA proposal against
accepted main `ec33cb5f01afa730da729790d3b9ab7f42524fe6`. The finalizer used
the unchanged authority registry from `compose-002`; no source, physical,
observer, or constructor computation was repeated.

The exact independent output audit compared decoded ownership rows with the
current-main baseline: the bank adds exactly the 65 reviewed proposed cells,
each from owner zero to its intended owner; it loses or reassigns no cell. Of
the original 133 MDA holds, all 68 owner-zero cells remain owner-zero. This is
a mechanical finalization consistency result, not scientific acceptance or
credit.

Pinned inputs and output hashes are recorded in `preparation.json`. In
particular, the selector input is blob `6e4df90224313c75215b87aca820e91ad0a8af72`
(SHA-256 `1aa3d317…`), the package-inputs input is blob
`ef1c0203a843a4156fc07b92de1566376b4ca6c5` (SHA-256 `6c341095…`), and the
resulting `startup-ownership.json` is SHA-256
`1f15b1a55fbdaf417c67e4386bd06795e470271053038de391d581797308109a`.
The finalizer lists 79 bank files, including 30 compatibility entries; those
compatibility assets remain pinned to the accepted baseline and were not
hydrated into this bounded checkout.

The original scope remains 1,986 cells: 1,853 previously accepted, 65
proposed, and 68 held. No hold is removed and no package-completion claim is
made here.
