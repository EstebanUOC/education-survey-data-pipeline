# Consolidate the school workbooks in R and run the pre/post analysis.
#
# The R version mirrors the Python pipeline for teams that work in R:
#   Rscript R/analysis.R data/raw outputs
# It reads every workbook with readxl, applies the range checks from
# config/validation_rules.csv, and fits a simple gain-score model.

suppressPackageStartupMessages({
  library(readxl); library(dplyr); library(tidyr); library(purrr)
  library(readr); library(ggplot2)
})

args <- commandArgs(trailingOnly = TRUE)
raw_dir <- if (length(args) >= 1) args[1] else "data/raw"
out_dir <- if (length(args) >= 2) args[2] else "outputs"
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

read_school <- function(path) {
  meta <- read_excel(path, sheet = "metadata")
  school <- meta$value[meta$field == "school_id"]
  map_dfr(c("pre", "post"), function(w) {
    read_excel(path, sheet = w) |>
      mutate(wave = w, school_id = school, source_file = basename(path),
             birth_date = as.Date(birth_date), assessment_date = as.Date(assessment_date))
  })
}

files <- list.files(raw_dir, pattern = "\\.xlsx$", full.names = TRUE)
data <- map_dfr(files, read_school)
message(sprintf("Read %d records from %d workbooks", nrow(data), length(files)))

# Range rules come from the same config file as the Python pipeline
rules <- read_csv("config/validation_rules.csv", show_col_types = FALSE) |>
  filter(check == "range", column %in% names(data))

issues <- pmap_dfr(rules, function(rule_id, column, min, max, severity, description, ...) {
  data |>
    filter(!is.na(.data[[column]]), .data[[column]] < min | .data[[column]] > max) |>
    transmute(school_id, wave, child_id, rule_id, column, value = as.character(.data[[column]]))
})
write_csv(issues, file.path(out_dir, "issues_log_R.csv"))

# Clean: one row per child and wave, out-of-range scores set to NA
scores <- c("vocabulary", "phonological_awareness", "letter_knowledge")
limits <- setNames(as.list(rules$max), rules$column)
clean <- data |>
  distinct(school_id, wave, child_id, .keep_all = TRUE) |>
  mutate(across(all_of(scores), ~ ifelse(.x < 0 | .x > limits[[cur_column()]], NA, .x)))
write_csv(clean, file.path(out_dir, "consolidated_R.csv"))

# Gain scores and a simple group comparison per measure
gains <- clean |>
  select(school_id, child_id, group, wave, all_of(scores)) |>
  pivot_longer(all_of(scores), names_to = "measure", values_to = "score") |>
  pivot_wider(names_from = wave, values_from = score) |>
  mutate(gain = post - pre)

results <- gains |>
  group_by(measure) |>
  group_modify(~ {
    fit <- lm(post ~ pre + group, data = .x)
    co <- summary(fit)$coefficients
    tibble(n = nobs(fit),
           group_effect = co["groupintervention", "Estimate"],
           p_value = co["groupintervention", "Pr(>|t|)"])
  })
write_csv(results, file.path(out_dir, "ancova_results_R.csv"))
print(results)

p <- gains |>
  group_by(measure, group) |>
  summarise(mean_gain = mean(gain, na.rm = TRUE), .groups = "drop") |>
  ggplot(aes(measure, mean_gain, fill = group)) +
  geom_col(position = "dodge") +
  labs(x = NULL, y = "Mean gain (post - pre)", fill = NULL) +
  theme_minimal()
ggsave(file.path(out_dir, "mean_gains_R.png"), p, width = 7, height = 3.5, dpi = 130)
