pacman::p_load(tidyverse, network, tidygraph, lubridate, ggraph, netrankr, extrafont, seriation, NetSwan, fastnet)


#' Takes in an edges dataframe to generate vertices
CreateGraph <- function(df) {
  vertices <- tibble(name=unique(c(df$from, df$to)))
  edges <- df
  
  graph <- tbl_graph(vertices, edges, directed = F) %>% 
    activate(nodes) %>% 
    mutate(date = as.Date(unique(df$date)[1]))
  
  return(graph)
}

#' Takes in a graph and outputs a DF with the nodes' measures by that unit, defined
#' by GetMeasures()
NodeMeasures <- function(graph) {
  # Insert specific output measures here
  graph <- graph %>%  
    activate(nodes) %>% 
    mutate(centrality_degreein = centrality_degree(mode="all", normalized=FALSE),
           pagerank = tidygraph::centrality_pagerank(),
           eigenvector_centrality = tidygraph::centrality_eigen(),
           hub_centrality = centrality_hub(),
           subgraph = centrality_subgraph())
  
  clustering_coef <- transitivity(graph)
  scaled_shannon_entropy <- diversity(graph)
  density <- igraph::edge_density(graph)
  
  node_data <- graph %>% 
    activate(nodes) %>% 
    as_tibble() %>% 
    cbind(clustering_coef) %>% 
    cbind(scaled_shannon_entropy) %>% 
    cbind(density)
  
  return(node_data)
}

#' Takes in a unit of date (e.g. day) and a directory (e.g. tidy_data.csv) to get
#' all node_measures defined in NodeMeasures
GetMeasures <- function(unit, df_data) {
  print(paste("Running analysis by", unit))
  df_data <- df_data %>% 
    mutate(timestamp = lubridate::as_datetime(timestamp/1000),
           date = round_date(timestamp, unit=unit),
           from = as.character(from),
           to = as.character(to)) %>% 
    filter(from!=to)
  df_data <- df_data %>% 
    group_split(date) %>% 
    map(CreateGraph) %>% 
    map_dfr(NodeMeasures)
  
  df_data %>% 
    cbind(unit=rep(unit, nrow(df_data))) %>% 
    return()
}


units = c("year", "month", "week", "day")

df <-read_csv("tidy_data.csv")

map_dfr(units, function(x) GetMeasures(unit=x, df)) %>% 
  write_csv("all_node_measures.csv")


