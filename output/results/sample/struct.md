# tables.json 구조

```text
tables: list[Table]
```

## Table

```text
table_id
section_index
table_index
xml_table_id
row_count
col_count
cell_spacing
border_fill_id_ref
border_fill
repeat_header
page_break
text_wrap
text_flow
width
height
pos_x
pos_y
treat_as_char
flow_with_text
in_margin_left
in_margin_right
in_margin_top
in_margin_bottom
out_margin_left
out_margin_right
out_margin_top
out_margin_bottom
caption_candidate
note_candidate
source_candidate
validation
semantic
raw_attrs
is_nested
parent_table_id
parent_cell_id
rows: list[TableRow]
```

## TableRow

```text
row_id
table_id
row_index
raw_attrs
cells: list[TableCell]
```

## TableCell

```text
cell_id
table_id
row_id
cell_index
name
header
has_margin
protect
editable
dirty
border_fill_id_ref
border_fill
row_addr
col_addr
row_span
col_span
end_row
end_col
width
height
margin_left
margin_right
margin_top
margin_bottom
sublist_raw_attrs
sublist_id
sublist_text_direction
sublist_line_wrap
sublist_vert_align
sublist_link_list_id_ref
sublist_link_list_next_id_ref
sublist_text_width
sublist_text_height
sublist_has_text_ref
sublist_has_num_ref
images: list[ImageInfo]
nested_tables: list[Table]
paragraphs: list[TableParagraph]
text
is_empty
has_image
has_field
has_shape
is_column_header
is_row_header
is_group_header
is_data_cell
raw_attrs
```

## ImageInfo

```text
image_id
parent_table_id
parent_cell_id
binary_item_id_ref
href
ref_id
width
height
raw_attrs
```

## TableParagraph

```text
paragraph_id
cell_id
paragraph_index
text
para_pr_id_ref
style_id_ref
raw_attrs
runs: list[TableRun]
```

## TableRun

```text
run_id
paragraph_id
run_index
text
char_pr_id_ref
has_line_break
has_tab
has_fw_space
raw_attrs
```
