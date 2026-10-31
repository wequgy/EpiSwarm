# EpiSwarm Studio: Data Sources Registry (`DATA_SOURCES.md`)

This registry tracks verified scientific citations, public datasets, and external resources utilized or supported by EpiSwarm Studio.

---

## 1. Scientific Literature & Reference Methodologies

1. **Libin et al. (2020)**
   - **Citation**: Pieter Libin, Timothy Verstraeten, Denis Roose, et al. *Deep reinforcement learning for large-scale epidemic control*. arXiv:2003.13676v1 [cs.LG], 2020.
   - **DOI/URL**: [https://arxiv.org/abs/2003.13676](https://arxiv.org/abs/2003.13676)
   - **Usage**: Multi-patch age-structured SEIR dynamics, discrete-time scale transformation for non-homogeneous Poisson commute arrivals, next-generation matrix spectral radius formulation, and reinforcement learning control space benchmarks.

2. **Prem et al. (2017, 2021)**
   - **Citation**: Prem K, Cook AR, Jit M. *Projecting social contact matrices in 152 countries using contact surveys and demographic data*. PLOS Computational Biology 13(9): e1005697. Extended 2021 in PLOS Med 18(2): e1008473.
   - **DOI/URL**: [https://doi.org/10.1371/journal.pcbi.1005697](https://doi.org/10.1371/journal.pcbi.1005697)
   - **Usage**: Synthetic age- and setting-specific contact matrices (home, school, work, other locations) across 16 five-year age cohorts for bundled country defaults.

3. **Levin et al. (2020)**
   - **Citation**: Levin AT, Hanage WP, Owusu-Boaitey N, et al. *Assessing the age-specific infection fatality rate of COVID-19: systematic review & meta-analysis*. European Journal of Epidemiology 35:1123-1138 (2020).
   - **DOI/URL**: [https://doi.org/10.1007/s10654-020-00698-1](https://doi.org/10.1007/s10654-020-00698-1)
   - **Usage**: Empirical anchor points for age-stratified infection fatality ratios ($0.4\%$ at age 55, $1.3\%$ at 65, $4.5\%$ at 75, $15\%$ at 85) via log-linear interpolation.

4. **Eames et al. (2012)**
   - **Citation**: Eames KTD, Tilston NL, Brooks-Pollock E, Edmunds WJ. *Measured social contacts in Great Britain: school terms and holidays*. Epidemiol Infect 140(12):2205-2210 (2012).
   - **Usage**: Relative conversational contact rate reductions between school term and school holiday settings.

---

## 2. Demographic & Spatial Repositories

1. **United Nations World Population Prospects (WPP 2022)**
   - **Publisher**: United Nations Department of Economic and Social Affairs, Population Division.
   - **URL**: [https://population.un.org/wpp/](https://population.un.org/wpp/)
   - **Usage**: Bundled age pyramid baseline distributions for national aggregates.

2. **OpenCity Data Portal (Bengaluru Reference Pack)**
   - **Publisher**: OpenCity Urban Data Portal.
   - **Datasets**: BBMP Ward Census 2011, BBMP Ward Public Goods, BBMP Ward Boundaries (2015 & 2022 revisions).
   - **Usage**: Reference empirical data for Appendix Bengaluru pack.

3. **Oxford COVID-19 Government Response Tracker (OxCGRT)**
   - **Publisher**: Blavatnik School of Government, University of Oxford.
   - **URL**: [https://www.bsg.ox.ac.uk/research/research-projects/covid-19-government-response-tracker](https://www.bsg.ox.ac.uk/research/research-projects/covid-19-government-response-tracker)
   - **Usage**: Policy timeline and stringency metrics for empirical timeline validation.
