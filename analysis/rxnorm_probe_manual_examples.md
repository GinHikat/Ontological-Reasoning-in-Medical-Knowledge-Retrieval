# RxNorm probe manual examples

## rxnorm_probe_example_policy

- `33` [1533:1563] `albuterolipratropium nebulizer`
  - baseline: `2108233` (SCDF) albuterol inhalation powder
  - probe: `435` (IN) albuterol
  - reason: `no_strength_to_ingredient` strength=False route= form=

- `50` [1444:1464] `prednisone giảm liều`
  - baseline: `582600` (BN|TMSY) prednisone intensol
  - probe: `8640` (IN|TMSY) prednisone
  - reason: `no_strength_to_ingredient` strength=False route= form=

- `74` [634:656] `iv morphineiv morphine`
  - baseline: `1728776` (SCDF) morphine injection
  - probe: `7052` (IN) morphine
  - reason: `no_strength_to_ingredient` strength=False route=iv form=

- `33` [1579:1603] `methylprednisolone 125mg`
  - baseline: `1743702` (SCDC|TMSY) methylprednisolone 125 mg
  - probe: `1743704` (PSN|SCD|SY|TMSY) methylprednisolone 125 mg injection
  - reason: `strength_to_scd` strength=True route= form=

- `50` [915:931] `prednisone 40 mg`
  - baseline: `451144` (SCDC|TMSY) prednisone 40 mg
  - probe: `429332` (SCD|TMSY) prednisone 40 mg oral tablet
  - reason: `strength_to_scd` strength=True route= form=

- `50` [1561:1580] `prednisone 40 mg/ng`
  - baseline: `451144` (SCDC|TMSY) prednisone 40 mg
  - probe: `429332` (SCD|TMSY) prednisone 40 mg oral tablet
  - reason: `strength_to_scd` strength=True route= form=

- `1` [2199:2216] `aspirin 325mg x 1`
  - baseline: `198466` (PSN|SCD|SY) aspirin 325 mg oral capsule
  - probe: `1191` (IN) aspirin
  - reason: `scd_tie_or_miss_fallback_ingredient` strength=True route= form=

- `22` [75:90] `aspirin 325mg h`
  - baseline: `198467` (PSN|SCD|SY) aspirin 325 mg delayed release oral tablet
  - probe: `1191` (IN) aspirin
  - reason: `scd_tie_or_miss_fallback_ingredient` strength=True route= form=

- `27` [1053:1079] `metoprolol 5mg iv x2
    C`
  - baseline: `250082` (SCD) metoprolol 5 mg/ml injectable solution
  - probe: `6918` (IN) metoprolol
  - reason: `scd_tie_or_miss_fallback_ingredient` strength=True route=iv form=

- `32` [1502:1518] `furosemide 40 mg`
  - baseline: `315971` (SCDC) furosemide 40 mg
  - probe: `4603` (IN) furosemide
  - reason: `scd_tie_or_miss_fallback_ingredient` strength=True route= form=

- `33` [1401:1418] `bumetanide 2mg iv`
  - baseline: `315502` (SCDC) bumetanide 2 mg
  - probe: `1808` (IN) bumetanide
  - reason: `scd_tie_or_miss_fallback_ingredient` strength=True route=iv form=

- `33` [1434:1451] `vancomycin 1 gram`
  - baseline: `1807512` (SCDC) vancomycin 1000 mg
  - probe: `11124` (IN) vancomycin
  - reason: `scd_tie_or_miss_fallback_ingredient` strength=True route= form=

- `33` [1504:1517] `aspirin 325mg`
  - baseline: `317300` (SCDC) aspirin 325 mg
  - probe: `1191` (IN) aspirin
  - reason: `scd_tie_or_miss_fallback_ingredient` strength=True route= form=

- `70` [171:190] `acetaminophen 500mg`
  - baseline: `315266` (SCDC) acetaminophen 500 mg
  - probe: `161` (IN) acetaminophen
  - reason: `scd_tie_or_miss_fallback_ingredient` strength=True route= form=

- `70` [1183:1202] `acetaminophen 500mg`
  - baseline: `315266` (SCDC) acetaminophen 500 mg
  - probe: `161` (IN) acetaminophen
  - reason: `scd_tie_or_miss_fallback_ingredient` strength=True route= form=

- `73` [760:772] `aspirin 81mg`
  - baseline: `315431` (SCDC) aspirin 81 mg
  - probe: `1191` (IN) aspirin
  - reason: `scd_tie_or_miss_fallback_ingredient` strength=True route= form=

- `73` [946:969] `atorvastatin 80mg daily`
  - baseline: `259255` (PSN|SCD|SY) atorvastatin 80 mg oral tablet
  - probe: `83367` (IN) atorvastatin
  - reason: `scd_tie_or_miss_fallback_ingredient` strength=True route= form=

- `84` [1291:1309] `Ceftriaxone 1 gram`
  - baseline: `1665020` (SCDC|TMSY) ceftriaxone 1000 mg
  - probe: `2193` (IN|TMSY) ceftriaxone
  - reason: `scd_tie_or_miss_fallback_ingredient` strength=True route= form=

### Suspicious / fallback-heavy

- `1` `aspirin 325mg x 1` → `1191` (scd_tie_or_miss_fallback_ingredient)
- `22` `aspirin 325mg h` → `1191` (scd_tie_or_miss_fallback_ingredient)
- `27` `metoprolol 5mg iv x2
    C` → `6918` (scd_tie_or_miss_fallback_ingredient)
- `32` `furosemide 40 mg` → `4603` (scd_tie_or_miss_fallback_ingredient)
- `33` `bumetanide 2mg iv` → `1808` (scd_tie_or_miss_fallback_ingredient)
- `33` `vancomycin 1 gram` → `11124` (scd_tie_or_miss_fallback_ingredient)
- `33` `aspirin 325mg` → `1191` (scd_tie_or_miss_fallback_ingredient)
- `70` `acetaminophen 500mg` → `161` (scd_tie_or_miss_fallback_ingredient)

## rxnorm_probe_ingredient_first

- `1` [2199:2216] `aspirin 325mg x 1`
  - baseline: `198466` (PSN|SCD|SY) aspirin 325 mg oral capsule
  - probe: `1191` (IN) aspirin
  - reason: `ingredient_first` strength=True route= form=

- `22` [75:90] `aspirin 325mg h`
  - baseline: `198467` (PSN|SCD|SY) aspirin 325 mg delayed release oral tablet
  - probe: `1191` (IN) aspirin
  - reason: `ingredient_first` strength=True route= form=

- `27` [1053:1079] `metoprolol 5mg iv x2
    C`
  - baseline: `250082` (SCD) metoprolol 5 mg/ml injectable solution
  - probe: `6918` (IN) metoprolol
  - reason: `ingredient_first` strength=True route=iv form=

- `32` [1502:1518] `furosemide 40 mg`
  - baseline: `315971` (SCDC) furosemide 40 mg
  - probe: `4603` (IN) furosemide
  - reason: `ingredient_first` strength=True route= form=

- `33` [1401:1418] `bumetanide 2mg iv`
  - baseline: `315502` (SCDC) bumetanide 2 mg
  - probe: `1808` (IN) bumetanide
  - reason: `ingredient_first` strength=True route=iv form=

- `33` [1434:1451] `vancomycin 1 gram`
  - baseline: `1807512` (SCDC) vancomycin 1000 mg
  - probe: `11124` (IN) vancomycin
  - reason: `ingredient_first` strength=True route= form=

- `33` [1467:1488] `levofloxacin 750mg iv`
  - baseline: `311296` (PSN|SCD|TMSY) levofloxacin 750 mg oral tablet
  - probe: `82122` (IN|TMSY) levofloxacin
  - reason: `ingredient_first` strength=True route=iv form=

- `33` [1504:1517] `aspirin 325mg`
  - baseline: `317300` (SCDC) aspirin 325 mg
  - probe: `1191` (IN) aspirin
  - reason: `ingredient_first` strength=True route= form=

- `33` [1533:1563] `albuterolipratropium nebulizer`
  - baseline: `2108233` (SCDF) albuterol inhalation powder
  - probe: `435` (IN) albuterol
  - reason: `ingredient_first` strength=False route= form=

- `33` [1579:1603] `methylprednisolone 125mg`
  - baseline: `1743702` (SCDC|TMSY) methylprednisolone 125 mg
  - probe: `6902` (IN|TMSY) methylprednisolone
  - reason: `ingredient_first` strength=True route= form=

- `50` [915:931] `prednisone 40 mg`
  - baseline: `451144` (SCDC|TMSY) prednisone 40 mg
  - probe: `8640` (IN|TMSY) prednisone
  - reason: `ingredient_first` strength=True route= form=

- `50` [1444:1464] `prednisone giảm liều`
  - baseline: `582600` (BN|TMSY) prednisone intensol
  - probe: `8640` (IN|TMSY) prednisone
  - reason: `ingredient_first` strength=False route= form=

- `50` [1561:1580] `prednisone 40 mg/ng`
  - baseline: `451144` (SCDC|TMSY) prednisone 40 mg
  - probe: `8640` (IN|TMSY) prednisone
  - reason: `ingredient_first` strength=True route= form=

- `70` [171:190] `acetaminophen 500mg`
  - baseline: `315266` (SCDC) acetaminophen 500 mg
  - probe: `161` (IN) acetaminophen
  - reason: `ingredient_first` strength=True route= form=

- `70` [1183:1202] `acetaminophen 500mg`
  - baseline: `315266` (SCDC) acetaminophen 500 mg
  - probe: `161` (IN) acetaminophen
  - reason: `ingredient_first` strength=True route= form=

- `73` [760:772] `aspirin 81mg`
  - baseline: `315431` (SCDC) aspirin 81 mg
  - probe: `1191` (IN) aspirin
  - reason: `ingredient_first` strength=True route= form=

- `73` [911:927] `lasix 40mg daily`
  - baseline: `200809` (PSN|SBD|SY) lasix 40 mg oral tablet
  - probe: `4603` (IN) furosemide
  - reason: `ingredient_first` strength=True route= form=

- `73` [946:969] `atorvastatin 80mg daily`
  - baseline: `259255` (PSN|SCD|SY) atorvastatin 80 mg oral tablet
  - probe: `83367` (IN) atorvastatin
  - reason: `ingredient_first` strength=True route= form=

- `73` [986:1008] `lisinopril 2.5mg daily`
  - baseline: `311353` (PSN|SCD) lisinopril 2.5 mg oral tablet
  - probe: `29046` (IN) lisinopril
  - reason: `ingredient_first` strength=True route= form=

- `73` [1025:1043] `ranexa 500mg daily`
  - baseline: `616495` (SBD|SY) ranolazine 500 mg extended release oral tablet [ranexa]
  - probe: `35829` (IN) ranolazine
  - reason: `ingredient_first` strength=True route= form=

### Suspicious / fallback-heavy

- `1` `aspirin 325mg x 1` → `1191` (ingredient_first)
- `22` `aspirin 325mg h` → `1191` (ingredient_first)
- `27` `metoprolol 5mg iv x2
    C` → `6918` (ingredient_first)
- `32` `furosemide 40 mg` → `4603` (ingredient_first)
- `33` `bumetanide 2mg iv` → `1808` (ingredient_first)
- `33` `vancomycin 1 gram` → `11124` (ingredient_first)
- `33` `levofloxacin 750mg iv` → `82122` (ingredient_first)
- `33` `aspirin 325mg` → `1191` (ingredient_first)

## rxnorm_probe_baseline_plus_ingredient

- `1` [2199:2216] `aspirin 325mg x 1`
  - baseline: `198466` (PSN|SCD|SY) aspirin 325 mg oral capsule
  - probe: `198466|1191` (PSN|SCD|SY;IN) aspirin 325 mg oral capsule|aspirin
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `22` [75:90] `aspirin 325mg h`
  - baseline: `198467` (PSN|SCD|SY) aspirin 325 mg delayed release oral tablet
  - probe: `198467|1191` (PSN|SCD|SY;IN) aspirin 325 mg delayed release oral tablet|aspirin
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `27` [1053:1079] `metoprolol 5mg iv x2
    C`
  - baseline: `250082` (SCD) metoprolol 5 mg/ml injectable solution
  - probe: `250082|6918` (SCD;IN) metoprolol 5 mg/ml injectable solution|metoprolol
  - reason: `baseline_plus_ingredient` strength=True route=iv form=

- `32` [1502:1518] `furosemide 40 mg`
  - baseline: `315971` (SCDC) furosemide 40 mg
  - probe: `315971|4603` (SCDC;IN) furosemide 40 mg|furosemide
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `33` [1401:1418] `bumetanide 2mg iv`
  - baseline: `315502` (SCDC) bumetanide 2 mg
  - probe: `315502|1808` (SCDC;IN) bumetanide 2 mg|bumetanide
  - reason: `baseline_plus_ingredient` strength=True route=iv form=

- `33` [1434:1451] `vancomycin 1 gram`
  - baseline: `1807512` (SCDC) vancomycin 1000 mg
  - probe: `1807512|11124` (SCDC;IN) vancomycin 1000 mg|vancomycin
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `33` [1467:1488] `levofloxacin 750mg iv`
  - baseline: `311296` (PSN|SCD|TMSY) levofloxacin 750 mg oral tablet
  - probe: `311296|82122` (PSN|SCD|TMSY;IN|TMSY) levofloxacin 750 mg oral tablet|levofloxacin
  - reason: `baseline_plus_ingredient` strength=True route=iv form=

- `33` [1504:1517] `aspirin 325mg`
  - baseline: `317300` (SCDC) aspirin 325 mg
  - probe: `317300|1191` (SCDC;IN) aspirin 325 mg|aspirin
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `33` [1533:1563] `albuterolipratropium nebulizer`
  - baseline: `2108233` (SCDF) albuterol inhalation powder
  - probe: `2108233|435` (SCDF;IN) albuterol inhalation powder|albuterol
  - reason: `baseline_plus_ingredient` strength=False route= form=

- `33` [1579:1603] `methylprednisolone 125mg`
  - baseline: `1743702` (SCDC|TMSY) methylprednisolone 125 mg
  - probe: `1743702|6902` (SCDC|TMSY;IN|TMSY) methylprednisolone 125 mg|methylprednisolone
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `50` [915:931] `prednisone 40 mg`
  - baseline: `451144` (SCDC|TMSY) prednisone 40 mg
  - probe: `451144|8640` (SCDC|TMSY;IN|TMSY) prednisone 40 mg|prednisone
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `50` [1444:1464] `prednisone giảm liều`
  - baseline: `582600` (BN|TMSY) prednisone intensol
  - probe: `582600|8640` (BN|TMSY;IN|TMSY) prednisone intensol|prednisone
  - reason: `baseline_plus_ingredient` strength=False route= form=

- `50` [1561:1580] `prednisone 40 mg/ng`
  - baseline: `451144` (SCDC|TMSY) prednisone 40 mg
  - probe: `451144|8640` (SCDC|TMSY;IN|TMSY) prednisone 40 mg|prednisone
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `70` [171:190] `acetaminophen 500mg`
  - baseline: `315266` (SCDC) acetaminophen 500 mg
  - probe: `315266|161` (SCDC;IN) acetaminophen 500 mg|acetaminophen
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `70` [1183:1202] `acetaminophen 500mg`
  - baseline: `315266` (SCDC) acetaminophen 500 mg
  - probe: `315266|161` (SCDC;IN) acetaminophen 500 mg|acetaminophen
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `73` [760:772] `aspirin 81mg`
  - baseline: `315431` (SCDC) aspirin 81 mg
  - probe: `315431|1191` (SCDC;IN) aspirin 81 mg|aspirin
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `73` [911:927] `lasix 40mg daily`
  - baseline: `200809` (PSN|SBD|SY) lasix 40 mg oral tablet
  - probe: `200809|4603` (PSN|SBD|SY;IN) lasix 40 mg oral tablet|furosemide
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `73` [946:969] `atorvastatin 80mg daily`
  - baseline: `259255` (PSN|SCD|SY) atorvastatin 80 mg oral tablet
  - probe: `259255|83367` (PSN|SCD|SY;IN) atorvastatin 80 mg oral tablet|atorvastatin
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `73` [986:1008] `lisinopril 2.5mg daily`
  - baseline: `311353` (PSN|SCD) lisinopril 2.5 mg oral tablet
  - probe: `311353|29046` (PSN|SCD;IN) lisinopril 2.5 mg oral tablet|lisinopril
  - reason: `baseline_plus_ingredient` strength=True route= form=

- `73` [1025:1043] `ranexa 500mg daily`
  - baseline: `616495` (SBD|SY) ranolazine 500 mg extended release oral tablet [ranexa]
  - probe: `616495|35829` (SBD|SY;IN) ranolazine 500 mg extended release oral tablet [ranexa]|ranolazine
  - reason: `baseline_plus_ingredient` strength=True route= form=

### Suspicious / fallback-heavy

- `1` `aspirin 325mg x 1` → `198466|1191` (baseline_plus_ingredient)
- `22` `aspirin 325mg h` → `198467|1191` (baseline_plus_ingredient)
- `27` `metoprolol 5mg iv x2
    C` → `250082|6918` (baseline_plus_ingredient)
- `32` `furosemide 40 mg` → `315971|4603` (baseline_plus_ingredient)
- `33` `bumetanide 2mg iv` → `315502|1808` (baseline_plus_ingredient)
- `33` `vancomycin 1 gram` → `1807512|11124` (baseline_plus_ingredient)
- `33` `levofloxacin 750mg iv` → `311296|82122` (baseline_plus_ingredient)
- `33` `aspirin 325mg` → `317300|1191` (baseline_plus_ingredient)

