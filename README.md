
<!-- README.md is generated from README.Rmd. Please edit that file -->

# COGNET

**Authors:** [Esben Kran](https://kran.ai) & [Jonathan Hvithamar
Rystrøm](https://linkedin.com/in/jonathan-rystroem) <br/>

**Started:** March 2021

[![License](https://img.shields.io/badge/License-MIT-blue)](#license)

## Overview

Data analysis project on a whole Cognitive Science student year before
and during the covid-19 pandemic lockdown in Denmark.

## Introduction to experiment

During 1.5 years, 28 students communicated intensely on the social
messaging app Facebook as part of the cognitive science bachelor’s
program at Aarhus University. These students voluntarily gave us their
highly anonymized data (see “Anonymization”). In a post-experimental
questionnaire, 100% reported that it was their main communication tool
in the study group and 87,5% reported that it was their main
communication tool with everyone from the study.

The anonymized data contains a message per row between two of the 27
users (28 minus 1 dropout). The weight of a message is for a direct
message, while a group message is weighted as where is the amount of
users in the group (the sender inclusive).

### Main documents

| Name                           | Description                                                                                                                  |
| :----------------------------- | :--------------------------------------------------------------------------------------------------------------------------- |
| `data_load.py`                 | Converts the compressed data folders to usable formats. Creates `raw_consensual.csv`, `tidy_data.csv` and `dropout_dat.csv`. |
| `convert.r`                    | Transforms the above messages-by-row data to different node-level network measures. Creates `all_node_measures.csv`.         |
| `brms_preprocessing.Rmd`       | Preprocesses data for brms. Creates `brms_model_data.csv`.                                                                   |
| `brms_analysis.Rmd`            | Bayesian analysis and visualization document using `brms`.                                                                   |
| `timeseries_visualization.Rmd` | Visualizes `all_node_measures.csv` by week in a range of different narrative graphs.                                         |
| `network_eda.Rmd`              | Explores one week of data around the lockdown as a static network. Preliminary work for `convert.r`.                         |

## License

Released under [MIT](/LICENSE) by [@rysias](https://github.com/rysias)
and [@esbenkc](https://github.com/esbenkc).
