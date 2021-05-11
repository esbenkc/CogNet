pacman::p_load(tidyverse, network, tidygraph, lubridate, ggraph, netrankr, extrafont, seriation, NetSwan, fastnet)

df <-read_csv("tidy_data.csv")

## CHANGE UNIT HERE
unit="year"



df <- df %>% 
  mutate(timestamp = lubridate::as_datetime(timestamp/1000),
         date = round_date(timestamp, unit=unit),
         from = as.character(from),
         to = as.character(to)) %>% 
  filter(from!=to)

start <- as.Date(range(df$timestamp)[1]) %>% round_date(unit=unit)
end <- as.Date(range(df$timestamp)[2]) %>% round_date(unit=unit)

current <- start

sum_df <- tibble()

while(current <= end){
  
  current_df <- df %>% 
    filter(date == round_date(current, unit=unit))
  
  vertices <- tibble(name=unique(c(df$from, df$to)))
  edges <- current_df
  
  graph <- tbl_graph(vertices, edges)
  
  
  # Insert specific output measures here
  graph <- graph %>%  
    activate(nodes) %>% 
    mutate(centrality_degreein = centrality_degree(weights=NULL, mode="in", loops=FALSE, normalized=FALSE))
  
  
  
  node_data <- graph %>% 
    activate(nodes) %>% 
    as_tibble()
  
  node_data <- node_data %>% 
    cbind(date=rep(current %>% round_date(unit=unit), nrow(node_data)))
  
  sum_df <- sum_df %>% 
    rbind(node_data)
  
  current <- current + duration(1, unit)
}

sum_df %>% write_csv(paste0("node_measures_", unit, ".csv"))