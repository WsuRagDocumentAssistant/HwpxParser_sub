# final_debug.json 산출물 스키마

문서 3종(성과평가보고서 / 수정사업계획서 / 연차평가보고서)의 **합집합**이다.
리스트는 전수 순회했고, 한 문서에만 나타나는 필드도 포함한다.

숫자 3개는 문서별 출현 횟수(성과평가 / 수정계획 / 연차평가)다.

```
필드 경로 1272개 (문서 3종 합집합)
동적 키로 접은 경로 2개:
    tables.analyzed[].hierarchy.structured_records[].source_cell_ids  (키 207종, 인스턴스 378)
    tables.analyzed[].hierarchy.structured_records[].values  (키 196종, 인스턴스 378)

====================================================================================================
검증 - 알려진 구조 대조
====================================================================================================
  [OK ] blocks_document.blocks[]                                       고정 스키마여야 함
  [OK ] tables.analyzed[].hierarchy.structured_records[].values        동적 키여야 함
  [OK ] tables.analyzed[].preprocess.cells[]                           고정 스키마여야 함
  [OK ] table_internal_blocks.internal_blocks[]                        고정 스키마여야 함
  [OK ] summary                                                        고정 스키마여야 함 (선택 필드 있음)
  [OK ] blocks_document.blocks[].depth_correction                      고정 스키마여야 함 (선택 필드 있음)
  [OK ] tables.analyzed[].hierarchy.structured_records[].source_cell_ids 동적 키여야 함

====================================================================================================
[summary]  필드 31개
====================================================================================================
  summary                                                    dict                 1      1      1  
  summary.contents_dir_path                                  str                  1      1      1  output\unpacked\sample\Content
  summary.error_count                                        int                  1      0      0  0
  summary.filename                                           str                  1      1      1  sample
  summary.header                                             dict                 1      1      1  
  summary.header.bullet_count                                int                  0      1      1  10
  summary.header.char_property_count                         int                  1      1      1  685
  summary.header.heading_level_count                         int                  1      0      0  412
  summary.header.numbering_count                             int                  0      1      1  6
  summary.header.para_property_count                         int                  1      1      1  412
  summary.header.style_count                                 int                  1      1      1  82
  summary.header.style_name_count                            int                  1      0      0  82
  summary.header.style_to_char_pr_count                      int                  1      0      0  82
  summary.header.style_to_para_pr_count                      int                  1      0      0  82
  summary.header_file_path                                   str                  1      0      0  output\unpacked\sample\Content
  summary.header_reference_validation                        dict                 1      0      0  
  summary.header_reference_validation.missing_char_pr_ref_ta int                  1      0      0  0
  summary.header_reference_validation.missing_para_pr_ref_ta int                  1      0      0  0
  summary.header_reference_validation.missing_style_ref_tabl int                  1      0      0  0
  summary.header_reference_validation.tables_with_missing_ch list                 1      0      0  
  summary.header_reference_validation.tables_with_missing_pa list                 1      0      0  
  summary.header_reference_validation.tables_with_missing_st list                 1      0      0  
  summary.image_dir_path                                     str                  1      0      0  output\unpacked\sample\BinData
  summary.invalid_table_count                                int                  1      0      0  0
  summary.invalid_table_ids                                  list                 1      0      0  
  summary.section_count                                      int                  1      1      1  5
  summary.source                                             str                  1      1      1  sample.zip
  summary.table_count                                        int                  1      1      1  85
  summary.total_issue_count                                  int                  1      0      0  0
  summary.unpacked_dir_path                                  str                  1      1      1  output\unpacked\sample
  summary.warning_count                                      int                  1      0      0  0

====================================================================================================
[tables]  필드 431개
====================================================================================================
  tables                                                     dict                 1      1      1  
  tables.analyzed                                            list                 1      1      1  
  tables.analyzed[].children                                 list               200    327    201  
  tables.analyzed[].grid                                     dict               200    327    201  
  tables.analyzed[].grid.col_count                           int                200    327    201  2
  tables.analyzed[].grid.issues                              list               200    327    201  
  tables.analyzed[].grid.row_count                           int                200    327    201  1
  tables.analyzed[].grid.slots                               list               200    327    201  
  tables.analyzed[].grid.slots[][].cell_id                   str               3066   8931   4944  section0_tbl0_1555357482_r0_c0
  tables.analyzed[].grid.slots[][].kind                      str               3066   8931   4944  origin
  tables.analyzed[].grid.slots[][].origin_col                int                916   3044   1770  0
  tables.analyzed[].grid.slots[][].origin_row                int                916   3044   1770  0
  tables.analyzed[].hierarchy                                dict               200    327    201  
  tables.analyzed[].hierarchy.body_cells                     list               200    327    201  
  tables.analyzed[].hierarchy.caption_or_note_cells          list               200    327    201  
  tables.analyzed[].hierarchy.columns                        list               170    224    156  
  tables.analyzed[].hierarchy.columns[].col_index            int                140    539    309  0
  tables.analyzed[].hierarchy.columns[].confidence           str                140    539    309  high
  tables.analyzed[].hierarchy.columns[].header_texts         list               140    539    309  
  tables.analyzed[].hierarchy.columns[].is_row_header        bool               140    539    309  True
  tables.analyzed[].hierarchy.columns[].name                 str                140    539    309  구분
  tables.analyzed[].hierarchy.columns[].source_header_rows   list               140    539    309  
  tables.analyzed[].hierarchy.columns[].warnings             list               140    539    309  
  tables.analyzed[].hierarchy.form_sections                  list                 2      5     21  
  tables.analyzed[].hierarchy.form_sections[].items          list                 6     19     25  
  tables.analyzed[].hierarchy.form_sections[].items[].key    str                 14     74     52  제목
  tables.analyzed[].hierarchy.form_sections[].items[].key_ce str                 14     74     52  section0_tbl1_1555357484_r0_c0
  tables.analyzed[].hierarchy.form_sections[].items[].row_ad int                 14     74     52  0
  tables.analyzed[].hierarchy.form_sections[].items[].value  str                 14     74     52  『2022~2024 대학혁신지원사업』 성과평가보고서
  tables.analyzed[].hierarchy.form_sections[].items[].value_ null/str            14     74     52  section0_tbl1_1555357484_r0_c0
  tables.analyzed[].hierarchy.form_sections[].section        str                  6     19     25  문서 제목
  tables.analyzed[].hierarchy.full_width_blocks              list                 1      1      1  
  tables.analyzed[].hierarchy.full_width_blocks[].cell_id    str                  2      2      2  section0_tbl1_1555357484_r9_c0
  tables.analyzed[].hierarchy.full_width_blocks[].has_nested bool                 2      2      2  True
  tables.analyzed[].hierarchy.full_width_blocks[].row_addr   int                  2      2      2  9
  tables.analyzed[].hierarchy.full_width_blocks[].text       str                  2      2      2  본 대학은『대학혁신지원사업』에 대하여 제반사항 등을 준
  tables.analyzed[].hierarchy.header_col_candidates          list               200    327    201  
  tables.analyzed[].hierarchy.header_col_candidates[].cols   list               194    307    175  
  tables.analyzed[].hierarchy.header_col_candidates[].confid str                194    307    175  high
  tables.analyzed[].hierarchy.header_col_candidates[].reason list               194    307    175  
  tables.analyzed[].hierarchy.header_col_candidates[].score  int                194    307    175  6
  tables.analyzed[].hierarchy.header_cols                    list               200    327    201  
  tables.analyzed[].hierarchy.header_row_candidates          list               200    327    201  
  tables.analyzed[].hierarchy.header_row_candidates[].confid str                278    465    253  high
  tables.analyzed[].hierarchy.header_row_candidates[].reason list               278    465    253  
  tables.analyzed[].hierarchy.header_row_candidates[].rows   list               278    465    253  
  tables.analyzed[].hierarchy.header_row_candidates[].score  int                278    465    253  5
  tables.analyzed[].hierarchy.header_rows                    list               200    327    201  
  tables.analyzed[].hierarchy.key_value_header               dict                 2     12      1  
  tables.analyzed[].hierarchy.key_value_header.key           str                  2     12      1  구분
  tables.analyzed[].hierarchy.key_value_header.value         str                  2     12      1  주요 내용
  tables.analyzed[].hierarchy.key_value_items                list                 3     16      4  
  tables.analyzed[].hierarchy.key_value_items[].key          str                  9     52      6  권역 구분
  tables.analyzed[].hierarchy.key_value_items[].value        str                  9     52      6  충청권
  tables.analyzed[].hierarchy.key_value_orientation          str                  5     22     25  row_pairs
  tables.analyzed[].hierarchy.key_value_records              list               200    327    201  
  tables.analyzed[].hierarchy.key_value_records[].key        str                  9     56      6  권역 구분
  tables.analyzed[].hierarchy.key_value_records[].key_cell_i str                  9     56      6  section0_tbl0_1555357482_r0_c0
  tables.analyzed[].hierarchy.key_value_records[].row_addr   int                  9     52      6  0
  tables.analyzed[].hierarchy.key_value_records[].source_cel list                 9     56      6  
  tables.analyzed[].hierarchy.key_value_records[].value      str                  9     56      6  충청권
  tables.analyzed[].hierarchy.key_value_records[].value_cell str                  9     56      6  section0_tbl0_1555357482_r0_c1
  tables.analyzed[].hierarchy.nested_table_refs              list               200    327    201  
  tables.analyzed[].hierarchy.nested_table_refs[].nested_tab str                115    114     80  section0_tbl1_1555357484_r9_c0
  tables.analyzed[].hierarchy.nested_table_refs[].nested_tab int                115    114     80  0
  tables.analyzed[].hierarchy.nested_table_refs[].parent_cel str                115    114     80  section0_tbl1_1555357484_r9_c0
  tables.analyzed[].hierarchy.quality                        dict               200    327    201  
  tables.analyzed[].hierarchy.quality.warnings               list               200    327    201  
  tables.analyzed[].hierarchy.quality.warnings[].code        str                287    363    325  SINGLE_ROW_TABLE
  tables.analyzed[].hierarchy.quality.warnings[].message     str                287    363    325  Header rows were not assigned 
  tables.analyzed[].hierarchy.quality.warnings[].severity    str                287    363    325  info
  tables.analyzed[].hierarchy.quality.warnings[].stage       str                287    363    325  header_rows_detection
  tables.analyzed[].hierarchy.raw_blocks                     list                 1      1     20  
  tables.analyzed[].hierarchy.raw_blocks[].cell_ids          list                14      3     99  
  tables.analyzed[].hierarchy.raw_blocks[].col_addrs         list                14      3     99  
  tables.analyzed[].hierarchy.raw_blocks[].col_spans         list                14      3     99  
  tables.analyzed[].hierarchy.raw_blocks[].row_addr          int                 14      3     99  3
  tables.analyzed[].hierarchy.raw_blocks[].row_spans         list                14      3     99  
  tables.analyzed[].hierarchy.raw_blocks[].texts             list                14      3     99  
  tables.analyzed[].hierarchy.raw_rows                       list               200    327    201  
  tables.analyzed[].hierarchy.raw_rows[].cell_ids            list               633   1485    643  
  tables.analyzed[].hierarchy.raw_rows[].col_addrs           list               633   1485    643  
  tables.analyzed[].hierarchy.raw_rows[].col_spans           list               633   1485    643  
  tables.analyzed[].hierarchy.raw_rows[].has_nested_table    bool               633   1485    643  False
  tables.analyzed[].hierarchy.raw_rows[].row_addr            int                633   1485    643  0
  tables.analyzed[].hierarchy.raw_rows[].row_spans           list               633   1485    643  
  tables.analyzed[].hierarchy.raw_rows[].texts               list               633   1485    643  
  tables.analyzed[].hierarchy.record_status                  str                170    224    156  not_applicable
  tables.analyzed[].hierarchy.record_warnings                list               170    224    156  
  tables.analyzed[].hierarchy.record_warnings[].code         str                157    241    166  HEADER_ROWS_NOT_FOUND
  tables.analyzed[].hierarchy.record_warnings[].message      str                157    241    166  Structured records are not app
  tables.analyzed[].hierarchy.record_warnings[].severity     str                157    241    166  warning
  tables.analyzed[].hierarchy.record_warnings[].stage        str                157    241    166  structured_records_generation
  tables.analyzed[].hierarchy.structured_records             list               170    224    156  
  tables.analyzed[].hierarchy.structured_records[].row_heade dict               151    173     54  
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  0      0      7  교육·연구 프로그램 개발 운영비
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  2      0      0  외식조리전공, 한식·조리과학전공, 외식·조리경영전공, 
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  0      0      3  
  tables.analyzed[].hierarchy.structured_records[].row_heade str                 39     28      0  교육 혁신 성과
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  4      0      0  혁신적수업 운영
  tables.analyzed[].hierarchy.structured_records[].row_heade str                 45      0      0  기본
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  2      7      0  호텔외식 조리대학
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  0      0      3  교육혁신지수
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  7      0      0  역량 기반
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  0     12      0  교육
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  8      0      0  Sol Career 특강 시리즈
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  0      7      0  대학혁신 위원회
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  6      0      0  2023 대학생 공공기술 창업아이디어 경진대회
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  0      2      0  
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  0      2      0  교양교육혁신지수
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  6      0      0  김OO
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  4      0      0  전공체험 및 모의면접
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  0     11      0  
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  0      9      0  글로벌융합비즈니스학과
  tables.analyzed[].hierarchy.structured_records[].row_heade str                  0     12      0  2019
  tables.analyzed[].hierarchy.structured_records[].row_index int                151    173     54  0
  tables.analyzed[].hierarchy.structured_records[].source_ce dict               151    173     54  
  tables.analyzed[].hierarchy.structured_records[].source_ce null/str           653    805    250  section0_tbl2_1557233175_r1_c1
  tables.analyzed[].hierarchy.structured_records[].source_ro int                151    173     54  1
  tables.analyzed[].hierarchy.structured_records[].values    dict               151    173     54  
  tables.analyzed[].hierarchy.structured_records[].values.{동 str                530    715    237  유연한 학사운영
  tables.analyzed[].hierarchy.structured_records[].warnings  list               151    173     54  
  tables.analyzed[].hierarchy.table_type                     str                200    327    201  key_value_table
  tables.analyzed[].hierarchy.title_cells                    list               200    327    201  
  tables.analyzed[].is_nested                                bool               200    327    201  False
  tables.analyzed[].owner_control_type                       null/str           200    327    201  footer
  tables.analyzed[].parent_cell_id                           null/str           200    327    201  section0_tbl1_1555357484_r9_c0
  tables.analyzed[].parent_table_id                          null/str           200    327    201  section0_tbl1_1555357484
  tables.analyzed[].preprocess                               dict               200    327    201  
  tables.analyzed[].preprocess.candidates                    dict               200    327    201  
  tables.analyzed[].preprocess.candidates.caption_candidate  null/str           200    327    201  【2022~2024 대학혁신지원사업 성과평가보고서 요약
  tables.analyzed[].preprocess.candidates.note_candidate     null               200    327    201  
  tables.analyzed[].preprocess.candidates.source_candidate   null               200    327    201  
  tables.analyzed[].preprocess.cells                         list               200    327    201  
  tables.analyzed[].preprocess.cells[].cell_id               str               2150   5887   3174  section0_tbl0_1555357482_r0_c0
  tables.analyzed[].preprocess.cells[].cell_index            int               2150   5887   3174  0
  tables.analyzed[].preprocess.cells[].flags                 dict              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].flags.dirty           bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].flags.editable        bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].flags.has_field       bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].flags.has_image       bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].flags.has_margin      bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].flags.has_shape       bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].flags.header          bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].flags.is_column_heade bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].flags.is_data_cell    bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].flags.is_empty        bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].flags.is_group_header bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].flags.is_row_header   bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].flags.protect         bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].name                  str               2150   5887   3174  
  tables.analyzed[].preprocess.cells[].objects               dict              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].objects.captions      list              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].objects.captions[].bi str                  6      0      0  image53
  tables.analyzed[].preprocess.cells[].objects.captions[].ca str                  6      0      0  section2_tbl2_1556041232_r2_c0
  tables.analyzed[].preprocess.cells[].objects.captions[].pa str                  6      0      0  pic
  tables.analyzed[].preprocess.cells[].objects.captions[].ra dict                 6      0      0  
  tables.analyzed[].preprocess.cells[].objects.captions[].ra str                  6      0      0  0
  tables.analyzed[].preprocess.cells[].objects.captions[].ra str                  6      0      0  283
  tables.analyzed[].preprocess.cells[].objects.captions[].ra str                  6      0      0  15307
  tables.analyzed[].preprocess.cells[].objects.captions[].ra str                  6      0      0  BOTTOM
  tables.analyzed[].preprocess.cells[].objects.captions[].ra str                  6      0      0  8504
  tables.analyzed[].preprocess.cells[].objects.captions[].te str                  6      0      0  [가상스튜디오형]
  tables.analyzed[].preprocess.cells[].objects.controls      list              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].objects.controls[].co str                  2      5      8  section3_tbl1_1556041762_r0_c1
  tables.analyzed[].preprocess.cells[].objects.controls[].co str                  2      5      8  footer
  tables.analyzed[].preprocess.cells[].objects.controls[].so str                  2      5      8  hp:footer
  tables.analyzed[].preprocess.cells[].objects.controls[].te str                  2      5      8  
  tables.analyzed[].preprocess.cells[].objects.draw_objects  list              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].objects.draw_objects[ int                106    118     14  0
  tables.analyzed[].preprocess.cells[].objects.draw_objects[ null/str           106    118     14  추진체계
  tables.analyzed[].preprocess.cells[].objects.draw_objects[ str                106    118     14  section0_tbl11_1557044723_r0_c
  tables.analyzed[].preprocess.cells[].objects.draw_objects[ str                106    118     14  container
  tables.analyzed[].preprocess.cells[].objects.image_ids     list              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].objects.images        list              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].objects.images[].bina str                161    206     24  image9
  tables.analyzed[].preprocess.cells[].objects.images[].imag str                161    206     24  section0_tbl1_1555357484_r9_c0
  tables.analyzed[].preprocess.cells[].objects.nested_table_ list              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].position              dict              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].position.col_addr     int               2150   5887   3174  0
  tables.analyzed[].preprocess.cells[].position.col_span     int               2150   5887   3174  1
  tables.analyzed[].preprocess.cells[].position.end_col      int               2150   5887   3174  0
  tables.analyzed[].preprocess.cells[].position.end_row      int               2150   5887   3174  0
  tables.analyzed[].preprocess.cells[].position.row_addr     int               2150   5887   3174  0
  tables.analyzed[].preprocess.cells[].position.row_span     int               2150   5887   3174  1
  tables.analyzed[].preprocess.cells[].row_id                str               2150   5887   3174  section0_tbl0_1555357482_row0
  tables.analyzed[].preprocess.cells[].size                  dict              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].size.height           int               2150   5887   3174  3394
  tables.analyzed[].preprocess.cells[].size.margin_bottom    int               2150   5887   3174  141
  tables.analyzed[].preprocess.cells[].size.margin_left      int               2150   5887   3174  141
  tables.analyzed[].preprocess.cells[].size.margin_right     int               2150   5887   3174  141
  tables.analyzed[].preprocess.cells[].size.margin_top       int               2150   5887   3174  141
  tables.analyzed[].preprocess.cells[].size.width            int               2150   5887   3174  3558
  tables.analyzed[].preprocess.cells[].style_features        dict              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].style_features.has_bo bool              2150   5887   3174  True
  tables.analyzed[].preprocess.cells[].style_features.has_ce bool              2150   5887   3174  True
  tables.analyzed[].preprocess.cells[].style_features.max_fo float             2150   5887   3174  12.0
  tables.analyzed[].preprocess.cells[].style_refs            dict              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].style_refs.auto_label list              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].style_refs.char_pr_id list              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].style_refs.para_pr_id list              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].style_refs.style_id_r list              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].sublist               dict              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].sublist.has_num_ref   bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].sublist.has_text_ref  bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].sublist.line_wrap     str               2150   5887   3174  BREAK
  tables.analyzed[].preprocess.cells[].sublist.link_list_id_ str               2150   5887   3174  0
  tables.analyzed[].preprocess.cells[].sublist.link_list_nex str               2150   5887   3174  0
  tables.analyzed[].preprocess.cells[].sublist.sublist_id    str               2150   5887   3174  
  tables.analyzed[].preprocess.cells[].sublist.text_directio str               2150   5887   3174  HORIZONTAL
  tables.analyzed[].preprocess.cells[].sublist.text_height   int               2150   5887   3174  0
  tables.analyzed[].preprocess.cells[].sublist.text_width    int               2150   5887   3174  0
  tables.analyzed[].preprocess.cells[].sublist.vert_align    str               2150   5887   3174  CENTER
  tables.analyzed[].preprocess.cells[].table_id              str               2150   5887   3174  section0_tbl0_1555357482
  tables.analyzed[].preprocess.cells[].text                  dict              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].text.has_auto_label   bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].text.has_fw_space     bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].text.has_line_break   bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].text.has_tab          bool              2150   5887   3174  False
  tables.analyzed[].preprocess.cells[].text.paragraph_auto_l list              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].text.paragraph_auto_l str                 57    184     51  9
  tables.analyzed[].preprocess.cells[].text.paragraph_auto_l bool                57    184     51  False
  tables.analyzed[].preprocess.cells[].text.paragraph_auto_l str                 57    184     51  bullet
  tables.analyzed[].preprocess.cells[].text.paragraph_auto_l int                 57    184     51  0
  tables.analyzed[].preprocess.cells[].text.paragraph_auto_l str                 57    184     51  -
  tables.analyzed[].preprocess.cells[].text.paragraph_count  int               2150   5887   3174  2
  tables.analyzed[].preprocess.cells[].text.paragraph_texts  list              2150   5887   3174  
  tables.analyzed[].preprocess.cells[].text.run_count        int               2150   5887   3174  2
  tables.analyzed[].preprocess.cells[].text.text             str               2150   5887   3174  권역
구분
  tables.analyzed[].preprocess.identity                      dict               200    327    201  
  tables.analyzed[].preprocess.identity.section_index        int                200    327    201  0
  tables.analyzed[].preprocess.identity.table_id             str                200    327    201  section0_tbl0_1555357482
  tables.analyzed[].preprocess.identity.table_index          int                200    327    201  0
  tables.analyzed[].preprocess.identity.xml_table_id         str                200    327    201  1555357482
  tables.analyzed[].preprocess.layout                        dict               200    327    201  
  tables.analyzed[].preprocess.layout.cell_spacing           int                200    327    201  0
  tables.analyzed[].preprocess.layout.col_count              int                200    327    201  2
  tables.analyzed[].preprocess.layout.flow_with_text         bool               200    327    201  True
  tables.analyzed[].preprocess.layout.height                 int                200    327    201  3394
  tables.analyzed[].preprocess.layout.in_margin_bottom       int                200    327    201  141
  tables.analyzed[].preprocess.layout.in_margin_left         int                200    327    201  141
  tables.analyzed[].preprocess.layout.in_margin_right        int                200    327    201  141
  tables.analyzed[].preprocess.layout.in_margin_top          int                200    327    201  141
  tables.analyzed[].preprocess.layout.out_margin_bottom      int                200    327    201  140
  tables.analyzed[].preprocess.layout.out_margin_left        int                200    327    201  140
  tables.analyzed[].preprocess.layout.out_margin_right       int                200    327    201  140
  tables.analyzed[].preprocess.layout.out_margin_top         int                200    327    201  140
  tables.analyzed[].preprocess.layout.page_break             bool               200    327    201  True
  tables.analyzed[].preprocess.layout.pos_x                  int                200    327    201  0
  tables.analyzed[].preprocess.layout.pos_y                  int                200    327    201  0
  tables.analyzed[].preprocess.layout.repeat_header          bool               200    327    201  True
  tables.analyzed[].preprocess.layout.row_count              int                200    327    201  1
  tables.analyzed[].preprocess.layout.text_flow              str                200    327    201  BOTH_SIDES
  tables.analyzed[].preprocess.layout.text_wrap              str                200    327    201  TOP_AND_BOTTOM
  tables.analyzed[].preprocess.layout.treat_as_char          bool               200    327    201  True
  tables.analyzed[].preprocess.layout.width                  int                200    327    201  11078
  tables.analyzed[].preprocess.nesting                       dict               200    327    201  
  tables.analyzed[].preprocess.nesting.child_table_count     int                200    327    201  0
  tables.analyzed[].preprocess.nesting.child_table_ids       list               200    327    201  
  tables.analyzed[].preprocess.nesting.depth                 int                200    327    201  0
  tables.analyzed[].preprocess.nesting.has_child_table       bool               200    327    201  False
  tables.analyzed[].preprocess.nesting.is_nested             bool               200    327    201  False
  tables.analyzed[].preprocess.nesting.owner_control_type    null/str           200    327    201  footer
  tables.analyzed[].preprocess.nesting.parent_cell_id        null/str           200    327    201  section0_tbl1_1555357484_r9_c0
  tables.analyzed[].preprocess.nesting.parent_table_id       null/str           200    327    201  section0_tbl1_1555357484
  tables.analyzed[].preprocess.objects                       dict               200    327    201  
  tables.analyzed[].preprocess.objects.binary_item_id_refs   list               200    327    201  
  tables.analyzed[].preprocess.objects.has_field             bool               200    327    201  False
  tables.analyzed[].preprocess.objects.has_image             bool               200    327    201  False
  tables.analyzed[].preprocess.objects.has_nested_table      bool               200    327    201  False
  tables.analyzed[].preprocess.objects.has_shape             bool               200    327    201  False
  tables.analyzed[].preprocess.objects.image_count           int                200    327    201  0
  tables.analyzed[].preprocess.objects.image_ids             list               200    327    201  
  tables.analyzed[].preprocess.objects.nested_table_count    int                200    327    201  0
  tables.analyzed[].preprocess.objects.nested_table_ids      list               200    327    201  
  tables.analyzed[].preprocess.structure                     dict               200    327    201  
  tables.analyzed[].preprocess.structure.col_span_cell_count int                200    327    201  0
  tables.analyzed[].preprocess.structure.empty_cell_count    int                200    327    201  0
  tables.analyzed[].preprocess.structure.full_width_cell_cou int                200    327    201  0
  tables.analyzed[].preprocess.structure.has_col_span        bool               200    327    201  False
  tables.analyzed[].preprocess.structure.has_full_width_cell bool               200    327    201  False
  tables.analyzed[].preprocess.structure.has_merged_cell     bool               200    327    201  False
  tables.analyzed[].preprocess.structure.has_row_span        bool               200    327    201  False
  tables.analyzed[].preprocess.structure.max_col_span        int                200    327    201  1
  tables.analyzed[].preprocess.structure.max_row_span        int                200    327    201  1
  tables.analyzed[].preprocess.structure.merged_cell_count   int                200    327    201  0
  tables.analyzed[].preprocess.structure.non_empty_cell_coun int                200    327    201  2
  tables.analyzed[].preprocess.structure.origin_cell_count   int                200    327    201  2
  tables.analyzed[].preprocess.structure.row_object_count    int                200    327    201  1
  tables.analyzed[].preprocess.structure.row_span_cell_count int                200    327    201  0
  tables.analyzed[].preprocess.style                         dict               200    327    201  
  tables.analyzed[].preprocess.style.char_pr_id_refs         list               200    327    201  
  tables.analyzed[].preprocess.style.para_pr_id_refs         list               200    327    201  
  tables.analyzed[].preprocess.style.style_id_refs           list               200    327    201  
  tables.analyzed[].preprocess.style_features                dict               200    327    201  
  tables.analyzed[].preprocess.style_features.avg_font_size  float              200    327    201  12.0
  tables.analyzed[].preprocess.style_features.bold_cell_coun int                200    327    201  2
  tables.analyzed[].preprocess.style_features.has_bold       bool               200    327    201  True
  tables.analyzed[].preprocess.style_features.has_center_ali bool               200    327    201  True
  tables.analyzed[].preprocess.style_features.max_font_size  float              200    327    201  12.0
  tables.analyzed[].preprocess.text                          dict               200    327    201  
  tables.analyzed[].preprocess.text.cell_texts               list               200    327    201  
  tables.analyzed[].preprocess.text.cell_texts[].cell_id     str               2150   5887   3174  section0_tbl0_1555357482_r0_c0
  tables.analyzed[].preprocess.text.cell_texts[].has_nested_ bool              2150   5887   3174  False
  tables.analyzed[].preprocess.text.cell_texts[].text        str               2150   5887   3174  권역
구분
  tables.analyzed[].preprocess.text.empty_text_cell_count    int                200    327    201  0
  tables.analyzed[].preprocess.text.has_multiline_cell       bool               200    327    201  True
  tables.analyzed[].preprocess.text.multiline_cell_count     int                200    327    201  1
  tables.analyzed[].preprocess.text.non_empty_text_cell_coun int                200    327    201  2
  tables.analyzed[].preprocess.text.paragraph_count          int                200    327    201  3
  tables.analyzed[].preprocess.text.plain_text               str                200    327    201  권역
구분
충청권
  tables.analyzed[].preprocess.text.plain_text_without_neste str                200    327    201  권역
구분
충청권
  tables.analyzed[].preprocess.text.run_count                int                200    327    201  3
  tables.analyzed[].preprocess.validation                    dict               200    327    201  
  tables.analyzed[].preprocess.validation.actual_cell_count  int                200    327    201  2
  tables.analyzed[].preprocess.validation.actual_max_col_cou int                200    327    201  2
  tables.analyzed[].preprocess.validation.actual_max_row_cou int                200    327    201  1
  tables.analyzed[].preprocess.validation.actual_tr_count    int                200    327    201  1
  tables.analyzed[].preprocess.validation.declared_col_count int                200    327    201  2
  tables.analyzed[].preprocess.validation.declared_row_count int                200    327    201  1
  tables.analyzed[].preprocess.validation.has_col_count_mism bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_duplicated_slo bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_empty_cell     bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_empty_slot     bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_invalid_cell_a bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_invalid_cell_s bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_margin_differe bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_missing_cell_a bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_missing_char_p bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_missing_para_p bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_missing_style_ bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_nested_object  bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_out_of_range_c bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_row_count_mism bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_row_order_mism bool               200    327    201  False
  tables.analyzed[].preprocess.validation.has_size_mismatch  bool               200    327    201  False
  tables.analyzed[].preprocess.validation.header_border_row_ list               200    327    201  
  tables.analyzed[].preprocess.validation.is_irregular       bool               200    327    201  False
  tables.analyzed[].preprocess.validation.is_valid           bool               200    327    201  True
  tables.analyzed[].preprocess.validation.issue_count        int                200    327    201  0
  tables.analyzed[].preprocess.validation.issues             list               200    327    201  
  tables.analyzed[].table_id                                 str                200    327    201  section0_tbl0_1555357482
  tables.body_linking                                        list                 1      1      1  
  tables.body_linking[].candidates                           dict               200    327    201  
  tables.body_linking[].candidates.caption_candidate         null/str           200    327    201  【2022~2024 대학혁신지원사업 성과평가보고서 요약
  tables.body_linking[].candidates.note_candidate            null               200    327    201  
  tables.body_linking[].candidates.source_candidate          null               200    327    201  
  tables.body_linking[].children                             list               200    327    201  
  tables.body_linking[].full_width_blocks                    list               200    327    201  
  tables.body_linking[].full_width_blocks[].cell_id          str                  2      2      2  section0_tbl1_1555357484_r9_c0
  tables.body_linking[].full_width_blocks[].has_nested_table bool                 2      2      2  True
  tables.body_linking[].full_width_blocks[].row_addr         int                  2      2      2  9
  tables.body_linking[].full_width_blocks[].text             str                  2      2      2  본 대학은『대학혁신지원사업』에 대하여 제반사항 등을 준
  tables.body_linking[].hierarchy                            dict               200    327    201  
  tables.body_linking[].hierarchy.caption_or_note_cells      list               200    327    201  
  tables.body_linking[].hierarchy.nested_table_refs          list               200    327    201  
  tables.body_linking[].hierarchy.nested_table_refs[].nested str                115    114     80  section0_tbl1_1555357484_r9_c0
  tables.body_linking[].hierarchy.nested_table_refs[].nested int                115    114     80  0
  tables.body_linking[].hierarchy.nested_table_refs[].parent str                115    114     80  section0_tbl1_1555357484_r9_c0
  tables.body_linking[].hierarchy.table_type                 str                200    327    201  key_value_table
  tables.body_linking[].hierarchy.title_cells                list               200    327    201  
  tables.body_linking[].identity                             dict               200    327    201  
  tables.body_linking[].identity.section_index               int                200    327    201  0
  tables.body_linking[].identity.table_index                 int                200    327    201  0
  tables.body_linking[].is_nested                            bool               200    327    201  False
  tables.body_linking[].layout                               dict               200    327    201  
  tables.body_linking[].layout.flow_with_text                bool               200    327    201  True
  tables.body_linking[].layout.height                        int                200    327    201  3394
  tables.body_linking[].layout.pos_x                         int                200    327    201  0
  tables.body_linking[].layout.pos_y                         int                200    327    201  0
  tables.body_linking[].layout.treat_as_char                 bool               200    327    201  True
  tables.body_linking[].layout.width                         int                200    327    201  11078
  tables.body_linking[].nesting                              dict               200    327    201  
  tables.body_linking[].nesting.child_table_ids              list               200    327    201  
  tables.body_linking[].nesting.depth                        int                200    327    201  0
  tables.body_linking[].nesting.has_child_table              bool               200    327    201  False
  tables.body_linking[].objects                              dict               200    327    201  
  tables.body_linking[].objects.binary_item_id_refs          list               200    327    201  
  tables.body_linking[].objects.has_field                    bool               200    327    201  False
  tables.body_linking[].objects.has_image                    bool               200    327    201  False
  tables.body_linking[].objects.has_nested_table             bool               200    327    201  False
  tables.body_linking[].objects.has_shape                    bool               200    327    201  False
  tables.body_linking[].objects.image_count                  int                200    327    201  0
  tables.body_linking[].objects.image_ids                    list               200    327    201  
  tables.body_linking[].objects.nested_table_count           int                200    327    201  0
  tables.body_linking[].objects.nested_table_ids             list               200    327    201  
  tables.body_linking[].parent_cell_id                       null/str           200    327    201  section0_tbl1_1555357484_r9_c0
  tables.body_linking[].parent_table_id                      null/str           200    327    201  section0_tbl1_1555357484
  tables.body_linking[].raw_blocks                           list               200    327    201  
  tables.body_linking[].raw_blocks[].cell_ids                list                14      3     99  
  tables.body_linking[].raw_blocks[].col_addrs               list                14      3     99  
  tables.body_linking[].raw_blocks[].col_spans               list                14      3     99  
  tables.body_linking[].raw_blocks[].row_addr                int                 14      3     99  3
  tables.body_linking[].raw_blocks[].row_spans               list                14      3     99  
  tables.body_linking[].raw_blocks[].texts                   list                14      3     99  
  tables.body_linking[].structure                            dict               200    327    201  
  tables.body_linking[].structure.col_span_cell_count        int                200    327    201  0
  tables.body_linking[].structure.empty_cell_count           int                200    327    201  0
  tables.body_linking[].structure.full_width_cell_count      int                200    327    201  0
  tables.body_linking[].structure.has_col_span               bool               200    327    201  False
  tables.body_linking[].structure.has_full_width_cell        bool               200    327    201  False
  tables.body_linking[].structure.has_merged_cell            bool               200    327    201  False
  tables.body_linking[].structure.has_row_span               bool               200    327    201  False
  tables.body_linking[].structure.max_col_span               int                200    327    201  1
  tables.body_linking[].structure.max_row_span               int                200    327    201  1
  tables.body_linking[].structure.merged_cell_count          int                200    327    201  0
  tables.body_linking[].structure.non_empty_cell_count       int                200    327    201  2
  tables.body_linking[].structure.origin_cell_count          int                200    327    201  2
  tables.body_linking[].structure.row_object_count           int                200    327    201  1
  tables.body_linking[].structure.row_span_cell_count        int                200    327    201  0
  tables.body_linking[].style_features                       dict               200    327    201  
  tables.body_linking[].style_features.avg_font_size         float              200    327    201  12.0
  tables.body_linking[].style_features.bold_cell_count       int                200    327    201  2
  tables.body_linking[].style_features.has_bold              bool               200    327    201  True
  tables.body_linking[].style_features.has_center_alignment  bool               200    327    201  True
  tables.body_linking[].style_features.max_font_size         float              200    327    201  12.0
  tables.body_linking[].table_id                             str                200    327    201  section0_tbl0_1555357482
  tables.body_linking[].text                                 dict               200    327    201  
  tables.body_linking[].text.cell_texts                      list               200    327    201  
  tables.body_linking[].text.cell_texts[].cell_id            str               2150   5887   3174  section0_tbl0_1555357482_r0_c0
  tables.body_linking[].text.cell_texts[].has_nested_table   bool              2150   5887   3174  False
  tables.body_linking[].text.cell_texts[].text               str               2150   5887   3174  권역
구분
  tables.body_linking[].text.plain_text                      str                200    327    201  권역
구분
충청권
  tables.body_linking[].text.plain_text_without_nested_table str                200    327    201  권역
구분
충청권
  tables.body_linking[].text_stats                           dict               200    327    201  
  tables.body_linking[].text_stats.empty_text_cell_count     int                200    327    201  0
  tables.body_linking[].text_stats.has_multiline_cell        bool               200    327    201  True
  tables.body_linking[].text_stats.multiline_cell_count      int                200    327    201  1
  tables.body_linking[].text_stats.non_empty_text_cell_count int                200    327    201  2
  tables.body_linking[].text_stats.paragraph_count           int                200    327    201  3
  tables.body_linking[].text_stats.run_count                 int                200    327    201  3

====================================================================================================
[blocks_document]  필드 316개
====================================================================================================
  blocks_document                                            dict                 1      1      1  
  blocks_document.blocks                                     list                 1      1      1  
  blocks_document.blocks[].anchor_paragraph_path             null/str           411   1110    605  Contents/section0.xml#hp:p[0]
  blocks_document.blocks[].anchor_reference                  dict/null          411   1110    605  
  blocks_document.blocks[].anchor_reference.anchor_paragraph str                160    324    184  Contents/section0.xml#hp:p[0]
  blocks_document.blocks[].anchor_reference.confidence       float              160    324    184  0.9
  blocks_document.blocks[].anchor_reference.source           str                160    324    184  raw_node
  blocks_document.blocks[].anchor_resolution                 dict                 8     71     24  
  blocks_document.blocks[].anchor_resolution.anchor_basis    str                  8     71     24  section_index+paragraph_index
  blocks_document.blocks[].anchor_resolution.anchor_block_id str                  8     71     24  s0_b00039
  blocks_document.blocks[].anchor_resolution.anchor_block_re int                  8     71     24  39
  blocks_document.blocks[].anchor_resolution.anchor_paragrap int                  8     71     24  27
  blocks_document.blocks[].anchor_resolution.anchor_section_ int                  8     71     24  0
  blocks_document.blocks[].anchor_resolution.confidence      float                8     71     24  0.9
  blocks_document.blocks[].anchor_resolution.order_policy    str                  8     71     24  after_anchor_paragraph_preserv
  blocks_document.blocks[].anchor_resolution.reason          null                 8     71     24  
  blocks_document.blocks[].anchor_resolution.status          str                  8     71     24  resolved
  blocks_document.blocks[].block_id                          str                411   1110    605  s0_b00000
  blocks_document.blocks[].block_type                        str                411   1110    605  paragraph
  blocks_document.blocks[].confidence_score                  float              411   1110    605  0.9
  blocks_document.blocks[].depth                             int                411   1110    605  1
  blocks_document.blocks[].depth_band                        str                411   1110    605  body
  blocks_document.blocks[].depth_candidates                  list               411   1110    605  
  blocks_document.blocks[].depth_candidates[].depth          int                442   1198    623  1
  blocks_document.blocks[].depth_candidates[].score          float              442   1198    623  0.9
  blocks_document.blocks[].depth_candidates[].signals        list               442   1198    623  
  blocks_document.blocks[].depth_constraint_decision         dict                 8      4      2  
  blocks_document.blocks[].depth_constraint_decision.action  str                  8      4      2  kept
  blocks_document.blocks[].depth_constraint_decision.new_dep int                  8      4      2  3
  blocks_document.blocks[].depth_constraint_decision.old_dep int                  8      4      2  3
  blocks_document.blocks[].depth_constraint_decision.reasons list                 8      4      2  
  blocks_document.blocks[].depth_constraint_decision.relaxat int                  8      4      2  2
  blocks_document.blocks[].depth_correction                  dict               290    683    490  
  blocks_document.blocks[].depth_correction.anchor_block_id  str                247    631    471  s0_b00055
  blocks_document.blocks[].depth_correction.anchor_scope_id  null/str           272    683    490  scope_001
  blocks_document.blocks[].depth_correction.applied          bool               290    683    490  False
  blocks_document.blocks[].depth_correction.carried_over_sco bool                30      0      0  True
  blocks_document.blocks[].depth_correction.delta            int                265    631    471  -4
  blocks_document.blocks[].depth_correction.indent_key       int                 14      0      0  1200
  blocks_document.blocks[].depth_correction.marker_class     str                 14      0      0  dot
  blocks_document.blocks[].depth_correction.min_allowed_dept int                199    525    403  3
  blocks_document.blocks[].depth_correction.new_depth        int                290    683    490  0
  blocks_document.blocks[].depth_correction.old_depth        int                290    683    490  0
  blocks_document.blocks[].depth_correction.ordinal_family   str                  1      0      0  hangul
  blocks_document.blocks[].depth_correction.ordinal_value    int                  1      0      0  2
  blocks_document.blocks[].depth_correction.outline_family   str                 25     52     19  toc_depth0_anchor
  blocks_document.blocks[].depth_correction.outline_level    int                 25     52     19  1
  blocks_document.blocks[].depth_correction.reason           str                290    683    490  toc_depth0_anchor
  blocks_document.blocks[].depth_correction.relative_level   int                 48    106     68  1
  blocks_document.blocks[].depth_source                      str                 23     63     16  toc_depth0_anchor
  blocks_document.blocks[].evidence                          list               411   1110    605  
  blocks_document.blocks[].heading_seed                      bool                23     63     16  True
  blocks_document.blocks[].layout_position                   dict               411   1110    605  
  blocks_document.blocks[].layout_position.anchor_type       null/str           411   1110    605  inline
  blocks_document.blocks[].layout_position.bounding_box_esti null               411   1110    605  
  blocks_document.blocks[].layout_position.page_number_estim null               411   1110    605  
  blocks_document.blocks[].layout_position.paragraph_index   int                411   1110    605  0
  blocks_document.blocks[].layout_position.size              dict/null          411   1110    605  
  blocks_document.blocks[].layout_position.size.height       str                 20     62     26  84186
  blocks_document.blocks[].layout_position.size.source_tag   str                 20     62     26  sz
  blocks_document.blocks[].layout_position.size.unit         str                 20     62     26  hwpunit
  blocks_document.blocks[].layout_position.size.width        str                 20     62     26  59528
  blocks_document.blocks[].layout_position.treat_as_char     null/str           411   1110    605  1
  blocks_document.blocks[].layout_position.xml_order_index   int                411   1110    605  0
  blocks_document.blocks[].layout_position.z_order           null/str           411   1110    605  0
  blocks_document.blocks[].line_features                     dict/null          411   1110    605  
  blocks_document.blocks[].line_features.has_line_break      bool               251    786    421  False
  blocks_document.blocks[].line_features.line_break_count    int                251    786    421  0
  blocks_document.blocks[].line_features.line_count          int                251    786    421  1
  blocks_document.blocks[].line_features.line_depth_candidat bool               251    786    421  False
  blocks_document.blocks[].line_features.line_segments       list/null          251    786    421  
  blocks_document.blocks[].line_features.line_segments[].cha list                 0      2      0  
  blocks_document.blocks[].line_features.line_segments[].lin int                  0      2      0  0
  blocks_document.blocks[].line_features.line_segments[].tex str                  0      2      0  (중점특성화 분야) 3S 중심으로 대학의 5대 분야 융
  blocks_document.blocks[].line_features.line_style_variatio float              251    786    421  0.0
  blocks_document.blocks[].normalized_text                   null/str           411   1110    605  『2022~2024 대학혁신지원사업
  blocks_document.blocks[].reading_order_index               int                411   1110    605  0
  blocks_document.blocks[].reading_order_resolution          dict                 8     71     24  
  blocks_document.blocks[].reading_order_resolution.order_ba str                  8     71     24  after_anchor_paragraph_preserv
  blocks_document.blocks[].reading_order_resolution.order_ch bool                 8     71     24  False
  blocks_document.blocks[].reading_order_resolution.order_co float                8     71     24  0.9
  blocks_document.blocks[].reading_order_resolution.original int                  8     71     24  40
  blocks_document.blocks[].reading_order_resolution.resolved int                  8     71     24  40
  blocks_document.blocks[].section_index                     int                411   1110    605  0
  blocks_document.blocks[].selected_depth_candidate_index    int                411   1110    605  0
  blocks_document.blocks[].semantic_role                     str                411   1110    605  empty_paragraph
  blocks_document.blocks[].source_element                    str                411   1110    605  hp:p
  blocks_document.blocks[].source_occurrence_index           int                411   1110    605  0
  blocks_document.blocks[].source_xml_path                   str                411   1110    605  Contents/section0.xml#hp:p[0]
  blocks_document.blocks[].structure_features                dict               411   1110    605  
  blocks_document.blocks[].structure_features.binary_item_id null/str           411   1110    605  image10
  blocks_document.blocks[].structure_features.child_object_s dict/null          411   1110    605  
  blocks_document.blocks[].structure_features.child_object_s int                  0      0      3  2
  blocks_document.blocks[].structure_features.child_object_s int                  0      5      0  1
  blocks_document.blocks[].structure_features.child_object_s int                 19      7     17  2
  blocks_document.blocks[].structure_features.contained_obje int/null           411   1110    605  3
  blocks_document.blocks[].structure_features.control_type   null/str           411   1110    605  colPr
  blocks_document.blocks[].structure_features.is_table_relat bool               411   1110    605  False
  blocks_document.blocks[].structure_features.object_type    null/str           411   1110    605  polygon
  blocks_document.blocks[].structure_features.table_id       null/str           411   1110    605  section0_tbl0_1555357482
  blocks_document.blocks[].structure_features.table_index    int                 85    213    117  0
  blocks_document.blocks[].structure_features.xml_table_id   str                 85    213    117  1555357482
  blocks_document.blocks[].style_features                    dict               411   1110    605  
  blocks_document.blocks[].style_features.alignment          str                251    786    421  JUSTIFY
  blocks_document.blocks[].style_features.auto_label         dict/null          251    786    421  
  blocks_document.blocks[].style_features.auto_label.bullet_ str                  0    248    102  5
  blocks_document.blocks[].style_features.auto_label.is_priv bool                 0    248    102  False
  blocks_document.blocks[].style_features.auto_label.label_k str                  0    248    102  bullet
  blocks_document.blocks[].style_features.auto_label.level   int                  0    248    102  0
  blocks_document.blocks[].style_features.auto_label.text    str                  0    248    102  ­
  blocks_document.blocks[].style_features.bold_ratio         float              251    786    421  0.0
  blocks_document.blocks[].style_features.char_pr_id_refs    list               251    786    421  
  blocks_document.blocks[].style_features.cluster_confidence float              116    388    183  0.85
  blocks_document.blocks[].style_features.cluster_role_candi str                116    388    183  section_heading
  blocks_document.blocks[].style_features.depth_rank_candida int/null           116    388    183  1
  blocks_document.blocks[].style_features.font_size          float              251    786    421  10.0
  blocks_document.blocks[].style_features.font_size_avg      float/null         251    786    421  31.0
  blocks_document.blocks[].style_features.heading_level_nati null               251    786    421  
  blocks_document.blocks[].style_features.heading_type       str                251    786    421  NONE
  blocks_document.blocks[].style_features.indent             int                251    786    421  0
  blocks_document.blocks[].style_features.margin_left        int                251    786    421  0
  blocks_document.blocks[].style_features.numbering_level    int/null           251    786    421  0
  blocks_document.blocks[].style_features.para_pr_id_ref     null/str           411   1110    605  1
  blocks_document.blocks[].style_features.resolved_para_pr_i str                251    786    421  1
  blocks_document.blocks[].style_features.style_cluster_id   str                116    388    183  C32
  blocks_document.blocks[].style_features.style_cluster_rank int/null           116    388    183  1
  blocks_document.blocks[].style_features.style_id_ref       null/str           411   1110    605  0
  blocks_document.blocks[].table_hierarchy_ref               dict                85    213    117  
  blocks_document.blocks[].table_hierarchy_ref.headers       dict                85    213    117  
  blocks_document.blocks[].table_hierarchy_ref.headers.has_h bool                85    213    117  False
  blocks_document.blocks[].table_hierarchy_ref.headers.has_h bool                85    213    117  False
  blocks_document.blocks[].table_hierarchy_ref.headers.heade list                85    213    117  
  blocks_document.blocks[].table_hierarchy_ref.headers.heade list                85    213    117  
  blocks_document.blocks[].table_hierarchy_ref.match_status  str                 85    213    117  matched
  blocks_document.blocks[].table_hierarchy_ref.nesting       dict                85    213    117  
  blocks_document.blocks[].table_hierarchy_ref.nesting.child int                 85    213    117  0
  blocks_document.blocks[].table_hierarchy_ref.nesting.child list                85    213    117  
  blocks_document.blocks[].table_hierarchy_ref.nesting.is_ne bool                85    213    117  False
  blocks_document.blocks[].table_hierarchy_ref.nesting.paren null                85    213    117  
  blocks_document.blocks[].table_hierarchy_ref.nesting.paren null                85    213    117  
  blocks_document.blocks[].table_hierarchy_ref.quality_warni list                85    213    117  
  blocks_document.blocks[].table_hierarchy_ref.record_status str                 85    213    117  not_applicable
  blocks_document.blocks[].table_hierarchy_ref.records       dict                85    213    117  
  blocks_document.blocks[].table_hierarchy_ref.records.raw_r int                 85    213    117  1
  blocks_document.blocks[].table_hierarchy_ref.records.struc int                 85    213    117  0
  blocks_document.blocks[].table_hierarchy_ref.size          dict                85    213    117  
  blocks_document.blocks[].table_hierarchy_ref.size.col_coun int                 85    213    117  2
  blocks_document.blocks[].table_hierarchy_ref.size.row_coun int                 85    213    117  1
  blocks_document.blocks[].table_hierarchy_ref.size.source   str                 85    213    117  grid
  blocks_document.blocks[].table_hierarchy_ref.table_id      str                 85    213    117  section0_tbl0_1555357482
  blocks_document.blocks[].table_hierarchy_ref.table_type    str                 85    213    117  key_value_table
  blocks_document.blocks[].table_hierarchy_ref.text_preview  null/str            85    213    117  권역 구분 충청권
  blocks_document.blocks[].table_hierarchy_ref.title_text    null/str            85    213    117  1 대학의 중장기 발전계획과 사업목표, 교육혁신 추진 
  blocks_document.blocks[].table_internal_ref                dict                85    213    117  
  blocks_document.blocks[].table_internal_ref.cell_group_cou int                 85    213    117  2
  blocks_document.blocks[].table_internal_ref.internal_block int                 85    213    117  5
  blocks_document.blocks[].table_internal_ref.max_absolute_d int                 85    213    117  4
  blocks_document.blocks[].table_internal_ref.max_local_dept int                 85    213    117  3
  blocks_document.blocks[].table_internal_ref.nested_table_r int                 85    213    117  0
  blocks_document.blocks[].table_internal_ref.output_file    str                 85    213    117  table_internal_blocks.json
  blocks_document.blocks[].table_internal_ref.row_group_coun int                 85    213    117  1
  blocks_document.blocks[].table_internal_ref.status         str                 85    213    117  generated
  blocks_document.blocks[].table_internal_ref.table_caption_ int                 85    213    117  0
  blocks_document.blocks[].table_internal_ref.table_control_ int                 85    213    117  0
  blocks_document.blocks[].table_internal_ref.table_object_r int                 85    213    117  0
  blocks_document.blocks[].table_internal_ref.text_block_cou int                 85    213    117  2
  blocks_document.blocks[].text_content                      null/str           411   1110    605  
  blocks_document.blocks[].toc_flow_correction               dict                21    264     40  
  blocks_document.blocks[].toc_flow_correction.new_depth     int                 21    264     40  2
  blocks_document.blocks[].toc_flow_correction.old_depth     int                 21    264     40  8
  blocks_document.blocks[].toc_flow_correction.reason        str                 21    264     40  toc_anchor_flow_propagation
  blocks_document.blocks[].toc_match                         dict                23     63     16  
  blocks_document.blocks[].toc_match.anchor_depth            int                 23     63     16  0
  blocks_document.blocks[].toc_match.match_method            str                 23     63     16  toc_depth0_sequential_normaliz
  blocks_document.blocks[].toc_match.matched                 bool                23     63     16  True
  blocks_document.blocks[].toc_match.toc_index               int                 23     63     16  0
  blocks_document.blocks[].toc_match.toc_numbering           str                 23     63     16  1
  blocks_document.blocks[].toc_match.toc_title               str                 23     63     16  대학의 중장기발전계획과 사업목표, 교육혁신 추진 로드맵
  blocks_document.blocks[].visibility                        dict               411   1110    605  
  blocks_document.blocks[].visibility.include_in_llm_context bool               411   1110    605  False
  blocks_document.blocks[].visibility.include_in_preview     bool               411   1110    605  False
  blocks_document.blocks[].visibility.include_in_raw_blocks  bool               411   1110    605  True
  blocks_document.blocks[].visibility.reason                 null/str           411   1110    605  empty_paragraph
  blocks_document.blocks[].warnings                          list               411   1110    605  
  blocks_document.document                                   dict                 1      1      1  
  blocks_document.document.block_count                       int                  1      1      1  411
  blocks_document.document.parser_version                    str                  1      1      1  block-depth-v1
  blocks_document.document.section_count                     int                  1      1      1  5
  blocks_document.document.source_type                       str                  1      1      1  hwpx
  blocks_document.document.style_summary                     dict                 1      1      1  
  blocks_document.document.style_summary.body_cluster_id     str                  1      1      1  C01
  blocks_document.document.style_summary.body_font_size      float                1      1      1  12.0
  blocks_document.document.style_summary.cluster_count       int                  1      1      1  41
  blocks_document.document.style_summary.depth_rank_count    int                  1      1      1  7
  blocks_document.document.style_summary.heading_cluster_cou int                  1      1      1  15
  blocks_document.quality                                    dict                 1      1      1  
  blocks_document.quality.block_type_counts                  dict                 1      1      1  
  blocks_document.quality.block_type_counts.caption          int                  0      1      0  1
  blocks_document.quality.block_type_counts.control          int                  1      1      1  27
  blocks_document.quality.block_type_counts.footer           int                  1      1      1  4
  blocks_document.quality.block_type_counts.header           int                  0      0      1  2
  blocks_document.quality.block_type_counts.image            int                  1      1      1  14
  blocks_document.quality.block_type_counts.paragraph        int                  1      1      1  251
  blocks_document.quality.block_type_counts.section_control  int                  1      1      1  5
  blocks_document.quality.block_type_counts.shape            int                  1      1      1  6
  blocks_document.quality.block_type_counts.shape_group      int                  1      1      1  19
  blocks_document.quality.block_type_counts.table            int                  1      1      1  85
  blocks_document.quality.depth_candidates                   dict                 1      1      1  
  blocks_document.quality.depth_candidates.blocks_with_multi int                  1      1      1  8
  blocks_document.quality.depth_candidates.heading_jump_rela int                  1      1      1  8
  blocks_document.quality.depth_constraints                  dict                 1      1      1  
  blocks_document.quality.depth_constraints.cluster_consiste float                1      1      1  1.0
  blocks_document.quality.depth_constraints.depth_changed_co int                  1      1      1  0
  blocks_document.quality.depth_constraints.propagated_flow_ int                  1      1      1  0
  blocks_document.quality.depth_constraints.relaxed_heading_ int                  1      1      1  0
  blocks_document.quality.depth_constraints.unchanged_jump_c int                  1      1      1  8
  blocks_document.quality.depth_jump_count                   int                  1      1      1  8
  blocks_document.quality.depth_update_log                   list                 1      1      1  
  blocks_document.quality.depth_update_log[].affected_by_hea null/str             0     22      0  s1_b00133
  blocks_document.quality.depth_update_log[].block_id        str                  0     22      0  s1_b00133
  blocks_document.quality.depth_update_log[].new_depth       int                  0     22      0  6
  blocks_document.quality.depth_update_log[].old_depth       int                  0     22      0  7
  blocks_document.quality.depth_update_log[].reason          str                  0     22      0  heading_jump_relaxation_adopte
  blocks_document.quality.floating_anchor_resolution         dict                 1      1      1  
  blocks_document.quality.floating_anchor_resolution.floatin int                  1      1      1  0
  blocks_document.quality.floating_anchor_resolution.floatin int                  1      1      1  8
  blocks_document.quality.floating_anchor_resolution.floatin int                  1      1      1  0
  blocks_document.quality.floating_anchor_resolution.floatin int                  1      1      1  8
  blocks_document.quality.floating_anchor_resolution.floatin int                  1      1      1  0
  blocks_document.quality.nested_control_skipped             dict                 1      1      1  
  blocks_document.quality.nested_control_skipped.by_containe dict                 1      1      1  
  blocks_document.quality.nested_control_skipped.by_containe int                  1      1      0  6
  blocks_document.quality.nested_control_skipped.by_containe int                  1      1      0  9
  blocks_document.quality.nested_control_skipped.by_containe int                  0      0      1  2
  blocks_document.quality.nested_control_skipped.by_containe int                  0      0      1  6
  blocks_document.quality.nested_control_skipped.by_containe int                  1      1      1  24
  blocks_document.quality.nested_control_skipped.by_containe int                  1      1      1  24
  blocks_document.quality.nested_control_skipped.by_containe int                  1      1      1  2
  blocks_document.quality.nested_control_skipped.by_containe int                  0      0      1  4
  blocks_document.quality.nested_control_skipped.by_containe int                  1      1      0  1
  blocks_document.quality.nested_control_skipped.by_containe int                  1      0      0  10
  blocks_document.quality.nested_control_skipped.total       int                  1      1      1  76
  blocks_document.quality.semantic_role_counts               dict                 1      1      1  
  blocks_document.quality.semantic_role_counts.body_text     int                  1      1      1  58
  blocks_document.quality.semantic_role_counts.caption       int                  0      1      0  1
  blocks_document.quality.semantic_role_counts.decorative_sh int                  0      1      0  1
  blocks_document.quality.semantic_role_counts.document_cont int                  1      1      1  32
  blocks_document.quality.semantic_role_counts.empty_paragra int                  1      1      1  135
  blocks_document.quality.semantic_role_counts.figure        int                  1      1      1  39
  blocks_document.quality.semantic_role_counts.list_item     int                  0      1      1  248
  blocks_document.quality.semantic_role_counts.page_footer   int                  1      1      1  4
  blocks_document.quality.semantic_role_counts.page_header   int                  0      0      1  2
  blocks_document.quality.semantic_role_counts.section_headi int                  1      1      1  58
  blocks_document.quality.semantic_role_counts.table         int                  1      1      1  85
  blocks_document.quality.table_hierarchy_link               dict                 1      1      1  
  blocks_document.quality.table_hierarchy_link.all_table_hie dict                 1      1      1  
  blocks_document.quality.table_hierarchy_link.all_table_hie int                  1      1      1  200
  blocks_document.quality.table_hierarchy_link.all_table_hie dict                 1      1      1  
  blocks_document.quality.table_hierarchy_link.all_table_hie int                  1      1      1  169
  blocks_document.quality.table_hierarchy_link.all_table_hie int                  1      1      1  2
  blocks_document.quality.table_hierarchy_link.all_table_hie int                  1      1      1  29
  blocks_document.quality.table_hierarchy_link.all_table_hie dict                 1      1      1  
  blocks_document.quality.table_hierarchy_link.all_table_hie int                  1      1      1  170
  blocks_document.quality.table_hierarchy_link.all_table_hie int                  1      1      1  5
  blocks_document.quality.table_hierarchy_link.all_table_hie int                  1      1      1  25
  blocks_document.quality.table_hierarchy_link.top_level_blo dict                 1      1      1  
  blocks_document.quality.table_hierarchy_link.top_level_blo int                  1      1      1  85
  blocks_document.quality.table_hierarchy_link.top_level_blo int                  1      1      1  0
  blocks_document.quality.table_hierarchy_link.top_level_blo dict                 1      1      1  
  blocks_document.quality.table_hierarchy_link.top_level_blo int                  1      1      1  51
  blocks_document.quality.table_hierarchy_link.top_level_blo int                  1      1      1  50
  blocks_document.quality.table_hierarchy_link.top_level_blo int                  1      1      1  45
  blocks_document.quality.table_hierarchy_link.top_level_blo int                  1      1      1  1
  blocks_document.quality.table_hierarchy_link.top_level_blo dict                 1      1      1  
  blocks_document.quality.table_hierarchy_link.top_level_blo int                  1      1      1  78
  blocks_document.quality.table_hierarchy_link.top_level_blo int                  1      1      1  1
  blocks_document.quality.table_hierarchy_link.top_level_blo int                  1      1      1  6
  blocks_document.quality.table_hierarchy_link.top_level_blo int                  1      1      1  85
  blocks_document.quality.table_hierarchy_link.top_level_blo dict                 1      1      1  
  blocks_document.quality.table_hierarchy_link.top_level_blo int                  1      1      1  57
  blocks_document.quality.table_hierarchy_link.top_level_blo int                  1      1      1  3
  blocks_document.quality.table_hierarchy_link.top_level_blo int                  1      1      1  25
  blocks_document.quality.toc_anchor_flow                    dict                 1      1      1  
  blocks_document.quality.toc_anchor_flow.flow_propagated_co int                  1      1      1  19
  blocks_document.quality.toc_anchor_flow.residual_clamped_c int                  1      1      1  2
  blocks_document.quality.toc_anchor_flow.toc_anchor_count   int                  1      1      1  23
  blocks_document.quality.toc_depth0_anchor                  dict                 1      1      1  
  blocks_document.quality.toc_depth0_anchor.anchor           dict                 1      1      1  
  blocks_document.quality.toc_depth0_anchor.anchor.block_id  str                  1      1      1  s0_b00046
  blocks_document.quality.toc_depth0_anchor.anchor.section_i int                  1      1      1  0
  blocks_document.quality.toc_depth0_anchor.anchor.table_id  str                  1      1      1  section0_tbl3_1557216891
  blocks_document.quality.toc_depth0_anchor.anchor_found     bool                 1      1      1  True
  blocks_document.quality.toc_depth0_anchor.anchor_levels    list                 1      1      1  
  blocks_document.quality.toc_depth0_anchor.depth0_entry_cou int                  1      1      1  9
  blocks_document.quality.toc_depth0_anchor.enabled          bool                 1      1      1  True
  blocks_document.quality.toc_depth0_anchor.entry_count_by_l dict                 1      1      1  
  blocks_document.quality.toc_depth0_anchor.entry_count_by_l int                  1      1      1  9
  blocks_document.quality.toc_depth0_anchor.entry_count_by_l int                  1      1      1  12
  blocks_document.quality.toc_depth0_anchor.entry_count_by_l int                  1      1      0  2
  blocks_document.quality.toc_depth0_anchor.entry_count_by_l int                  0      1      0  10
  blocks_document.quality.toc_depth0_anchor.matched_block_id list                 1      1      1  
  blocks_document.quality.toc_depth0_anchor.matched_block_id dict                 1      1      1  
  blocks_document.quality.toc_depth0_anchor.matched_block_id list                 1      1      1  
  blocks_document.quality.toc_depth0_anchor.matched_block_id list                 1      1      1  
  blocks_document.quality.toc_depth0_anchor.matched_block_id list                 1      1      0  
  blocks_document.quality.toc_depth0_anchor.matched_block_id list                 0      1      0  
  blocks_document.quality.toc_depth0_anchor.matched_count    int                  1      1      1  9
  blocks_document.quality.toc_depth0_anchor.matched_count_by dict                 1      1      1  
  blocks_document.quality.toc_depth0_anchor.matched_count_by int                  1      1      1  9
  blocks_document.quality.toc_depth0_anchor.matched_count_by int                  1      1      1  12
  blocks_document.quality.toc_depth0_anchor.matched_count_by int                  1      1      0  2
  blocks_document.quality.toc_depth0_anchor.matched_count_by int                  0      1      0  7
  blocks_document.quality.toc_depth0_anchor.toc_entry_count  int                  1      1      1  29
  blocks_document.quality.toc_depth0_anchor.toc_source_table list                 1      1      1  
  blocks_document.quality.toc_depth0_anchor.unmatched_count  int                  1      1      1  0
  blocks_document.quality.unresolved_blocks                  list                 1      1      1  

====================================================================================================
[table_internal_blocks]  필드 44개
====================================================================================================
  table_internal_blocks                                      dict                 1      1      1  
  table_internal_blocks.document                             dict                 1      1      1  
  table_internal_blocks.document.internal_block_count        int                  1      1      1  5072
  table_internal_blocks.document.source_type                 str                  1      1      1  hwpx
  table_internal_blocks.document.stage                       str                  1      1      1  7.5-B
  table_internal_blocks.document.top_level_table_count       int                  1      1      1  85
  table_internal_blocks.internal_blocks                      list                 1      1      1  
  table_internal_blocks.internal_blocks[].absolute_depth     int               5072  13117   6263  2
  table_internal_blocks.internal_blocks[].binary_item_id_ref null/str           273    324     38  image9
  table_internal_blocks.internal_blocks[].depth_origin       str               5072  13117   6263  table_local_offset
  table_internal_blocks.internal_blocks[].evidence           list              5072  13117   6263  
  table_internal_blocks.internal_blocks[].internal_block_id  str               5072  13117   6263  section0_tbl0_1555357482::row0
  table_internal_blocks.internal_blocks[].internal_block_typ str               5072  13117   6263  table_row_group
  table_internal_blocks.internal_blocks[].local_depth        int               5072  13117   6263  1
  table_internal_blocks.internal_blocks[].local_order_index  int               5072  13117   6263  0
  table_internal_blocks.internal_blocks[].normalized_text    null/str          1843   5052   2129  권역 구분
  table_internal_blocks.internal_blocks[].object_text        null/str           267    324     38  추진체계
  table_internal_blocks.internal_blocks[].object_type        str                275    329     46  image
  table_internal_blocks.internal_blocks[].paragraph_auto_lab list              1835   5047   2121  
  table_internal_blocks.internal_blocks[].paragraph_auto_lab str                 57    184     51  9
  table_internal_blocks.internal_blocks[].paragraph_auto_lab bool                57    184     51  False
  table_internal_blocks.internal_blocks[].paragraph_auto_lab str                 57    184     51  bullet
  table_internal_blocks.internal_blocks[].paragraph_auto_lab int                 57    184     51  0
  table_internal_blocks.internal_blocks[].paragraph_auto_lab str                 57    184     51  -
  table_internal_blocks.internal_blocks[].paragraph_texts    list              1835   5047   2121  
  table_internal_blocks.internal_blocks[].parent_cell_id     null/str          5072  13117   6263  section0_tbl1_1555357484_r9_c0
  table_internal_blocks.internal_blocks[].parent_internal_bl null/str          5072  13117   6263  section0_tbl0_1555357482::row0
  table_internal_blocks.internal_blocks[].parent_table_id    null/str          5072  13117   6263  section0_tbl1_1555357484
  table_internal_blocks.internal_blocks[].root_table_id      str               5072  13117   6263  section0_tbl0_1555357482
  table_internal_blocks.internal_blocks[].section_index      int               5072  13117   6263  0
  table_internal_blocks.internal_blocks[].source_block_id    null/str          5072  13117   6263  s0_b00006
  table_internal_blocks.internal_blocks[].source_table_id    str               5072  13117   6263  section0_tbl0_1555357482
  table_internal_blocks.internal_blocks[].table_index        int               5072  13117   6263  0
  table_internal_blocks.internal_blocks[].text_content       null/str          5072  13117   6263  권역
구분
  table_internal_blocks.tables                               list                 1      1      1  
  table_internal_blocks.tables[].base_depth                  int/null            85    213    121  1
  table_internal_blocks.tables[].internal_block_count        int                 85    213    121  5
  table_internal_blocks.tables[].record_status               str                 85    213    121  not_applicable
  table_internal_blocks.tables[].root_table_id               str                 85    213    121  section0_tbl0_1555357482
  table_internal_blocks.tables[].section_index               int                 85    213    121  0
  table_internal_blocks.tables[].source_block_id             null/str            85    213    121  s0_b00006
  table_internal_blocks.tables[].table_id                    str                 85    213    121  section0_tbl0_1555357482
  table_internal_blocks.tables[].table_index                 int                 85    213    121  0
  table_internal_blocks.tables[].table_type                  str                 85    213    121  key_value_table

====================================================================================================
[warnings]  필드 10개
====================================================================================================
  warnings                                                   list                 1      1      1  
  warnings[].block_id                                        null/str           160    245    194  s0_b00019
  warnings[].evidence                                        dict/list          160    245    194  
  warnings[].evidence.internal_block_id                      str                  0      0     13  section0_tbl114_1256235548::ro
  warnings[].evidence.source_block_id                        null                 0      0     13  
  warnings[].message                                         str                160    245    194  depth jump retained by constra
  warnings[].severity                                        str                160    245    194  info
  warnings[].source_stage                                    str                160    245    194  stage8b
  warnings[].text_preview                                    null/str           160    245    194  2024. 6.
  warnings[].warning_code                                    str                160    245    194  unchanged_depth_jump

====================================================================================================
[quality_report]  필드 440개
====================================================================================================
  quality_report                                             dict                 1      1      1  
  quality_report.block_type_distribution                     dict                 1      1      1  
  quality_report.block_type_distribution.caption             int                  0      1      0  1
  quality_report.block_type_distribution.control             int                  1      1      1  27
  quality_report.block_type_distribution.footer              int                  1      1      1  4
  quality_report.block_type_distribution.header              int                  0      0      1  2
  quality_report.block_type_distribution.image               int                  1      1      1  14
  quality_report.block_type_distribution.paragraph           int                  1      1      1  251
  quality_report.block_type_distribution.section_control     int                  1      1      1  5
  quality_report.block_type_distribution.shape               int                  1      1      1  6
  quality_report.block_type_distribution.shape_group         int                  1      1      1  19
  quality_report.block_type_distribution.table               int                  1      1      1  85
  quality_report.cluster_consistency_score                   float                1      1      1  0.638
  quality_report.cluster_depth_consistency                   dict                 1      1      1  
  quality_report.cluster_depth_consistency.cluster_consisten float                1      1      1  0.638
  quality_report.cluster_depth_consistency.clusters          dict                 1      1      1  
  quality_report.cluster_depth_consistency.clusters.C05      dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C05.dept dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C05.dept int                  0      0      1  6
  quality_report.cluster_depth_consistency.clusters.C05.dept int                  1      0      1  7
  quality_report.cluster_depth_consistency.clusters.C05.dept int                  1      0      0  8
  quality_report.cluster_depth_consistency.clusters.C05.dept int                  1      0      0  5
  quality_report.cluster_depth_consistency.clusters.C05.memb int                  1      0      1  20
  quality_report.cluster_depth_consistency.clusters.C05.pref int                  1      0      1  3
  quality_report.cluster_depth_consistency.clusters.C05.pref float                1      0      1  0.4
  quality_report.cluster_depth_consistency.clusters.C07      dict                 1      1      1  
  quality_report.cluster_depth_consistency.clusters.C07.dept dict                 1      1      1  
  quality_report.cluster_depth_consistency.clusters.C07.dept int                  1      0      1  7
  quality_report.cluster_depth_consistency.clusters.C07.dept int                  1      1      0  2
  quality_report.cluster_depth_consistency.clusters.C07.memb int                  1      1      1  9
  quality_report.cluster_depth_consistency.clusters.C07.pref int                  1      1      1  2
  quality_report.cluster_depth_consistency.clusters.C07.pref float                1      1      1  0.778
  quality_report.cluster_depth_consistency.clusters.C08      dict                 1      1      0  
  quality_report.cluster_depth_consistency.clusters.C08.dept dict                 1      1      0  
  quality_report.cluster_depth_consistency.clusters.C08.dept int                  1      1      0  4
  quality_report.cluster_depth_consistency.clusters.C08.dept int                  1      1      0  4
  quality_report.cluster_depth_consistency.clusters.C08.dept int                  1      1      0  1
  quality_report.cluster_depth_consistency.clusters.C08.memb int                  1      1      0  9
  quality_report.cluster_depth_consistency.clusters.C08.pref int                  1      1      0  1
  quality_report.cluster_depth_consistency.clusters.C08.pref float                1      1      0  0.444
  quality_report.cluster_depth_consistency.clusters.C10      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C10.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C10.dept int                  0      1      0  22
  quality_report.cluster_depth_consistency.clusters.C10.memb int                  0      1      0  22
  quality_report.cluster_depth_consistency.clusters.C10.pref int                  0      1      0  3
  quality_report.cluster_depth_consistency.clusters.C10.pref float                0      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C11      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C11.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C11.dept int                  0      1      0  6
  quality_report.cluster_depth_consistency.clusters.C11.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C11.dept int                  0      1      0  16
  quality_report.cluster_depth_consistency.clusters.C11.dept int                  0      1      0  2
  quality_report.cluster_depth_consistency.clusters.C11.memb int                  0      1      0  25
  quality_report.cluster_depth_consistency.clusters.C11.pref int                  0      1      0  4
  quality_report.cluster_depth_consistency.clusters.C11.pref float                0      1      0  0.64
  quality_report.cluster_depth_consistency.clusters.C13      dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C13.dept dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C13.dept int                  0      0      1  6
  quality_report.cluster_depth_consistency.clusters.C13.memb int                  0      0      1  6
  quality_report.cluster_depth_consistency.clusters.C13.pref int                  0      0      1  3
  quality_report.cluster_depth_consistency.clusters.C13.pref float                0      0      1  1.0
  quality_report.cluster_depth_consistency.clusters.C15      dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C15.dept dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C15.dept int                  0      0      1  4
  quality_report.cluster_depth_consistency.clusters.C15.memb int                  0      0      1  4
  quality_report.cluster_depth_consistency.clusters.C15.pref int                  0      0      1  1
  quality_report.cluster_depth_consistency.clusters.C15.pref float                0      0      1  1.0
  quality_report.cluster_depth_consistency.clusters.C16      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C16.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C16.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C16.dept int                  0      1      0  5
  quality_report.cluster_depth_consistency.clusters.C16.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C16.memb int                  0      1      0  7
  quality_report.cluster_depth_consistency.clusters.C16.pref int                  0      1      0  2
  quality_report.cluster_depth_consistency.clusters.C16.pref float                0      1      0  0.714
  quality_report.cluster_depth_consistency.clusters.C17      dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C17.dept dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C17.dept int                  0      0      1  4
  quality_report.cluster_depth_consistency.clusters.C17.memb int                  0      0      1  4
  quality_report.cluster_depth_consistency.clusters.C17.pref int                  0      0      1  3
  quality_report.cluster_depth_consistency.clusters.C17.pref float                0      0      1  1.0
  quality_report.cluster_depth_consistency.clusters.C19      dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C19.dept dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C19.dept int                  0      0      1  2
  quality_report.cluster_depth_consistency.clusters.C19.memb int                  0      0      1  2
  quality_report.cluster_depth_consistency.clusters.C19.pref int                  0      0      1  2
  quality_report.cluster_depth_consistency.clusters.C19.pref float                0      0      1  1.0
  quality_report.cluster_depth_consistency.clusters.C20      dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C20.dept dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C20.dept int                  1      0      0  1
  quality_report.cluster_depth_consistency.clusters.C20.dept int                  1      0      0  3
  quality_report.cluster_depth_consistency.clusters.C20.dept int                  0      0      1  3
  quality_report.cluster_depth_consistency.clusters.C20.memb int                  1      0      1  4
  quality_report.cluster_depth_consistency.clusters.C20.pref int                  1      0      1  2
  quality_report.cluster_depth_consistency.clusters.C20.pref float                1      0      1  0.75
  quality_report.cluster_depth_consistency.clusters.C21      dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C21.dept dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C21.dept int                  0      0      1  1
  quality_report.cluster_depth_consistency.clusters.C21.memb int                  0      0      1  1
  quality_report.cluster_depth_consistency.clusters.C21.pref int                  0      0      1  4
  quality_report.cluster_depth_consistency.clusters.C21.pref float                0      0      1  1.0
  quality_report.cluster_depth_consistency.clusters.C22      dict                 0      1      1  
  quality_report.cluster_depth_consistency.clusters.C22.dept dict                 0      1      1  
  quality_report.cluster_depth_consistency.clusters.C22.dept int                  0      0      1  2
  quality_report.cluster_depth_consistency.clusters.C22.dept int                  0      1      0  5
  quality_report.cluster_depth_consistency.clusters.C22.memb int                  0      1      1  5
  quality_report.cluster_depth_consistency.clusters.C22.pref int                  0      1      1  3
  quality_report.cluster_depth_consistency.clusters.C22.pref float                0      1      1  1.0
  quality_report.cluster_depth_consistency.clusters.C23      dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C23.dept dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C23.dept int                  0      0      1  2
  quality_report.cluster_depth_consistency.clusters.C23.dept int                  1      0      0  3
  quality_report.cluster_depth_consistency.clusters.C23.memb int                  1      0      1  3
  quality_report.cluster_depth_consistency.clusters.C23.pref int                  1      0      1  6
  quality_report.cluster_depth_consistency.clusters.C23.pref float                1      0      1  1.0
  quality_report.cluster_depth_consistency.clusters.C26      dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C26.dept dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C26.dept int                  1      0      0  1
  quality_report.cluster_depth_consistency.clusters.C26.dept int                  1      0      1  1
  quality_report.cluster_depth_consistency.clusters.C26.memb int                  1      0      1  2
  quality_report.cluster_depth_consistency.clusters.C26.pref int                  1      0      1  3
  quality_report.cluster_depth_consistency.clusters.C26.pref float                1      0      1  0.5
  quality_report.cluster_depth_consistency.clusters.C27      dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C27.dept dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C27.dept int                  0      0      1  2
  quality_report.cluster_depth_consistency.clusters.C27.memb int                  0      0      1  2
  quality_report.cluster_depth_consistency.clusters.C27.pref int                  0      0      1  3
  quality_report.cluster_depth_consistency.clusters.C27.pref float                0      0      1  1.0
  quality_report.cluster_depth_consistency.clusters.C28      dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C28.dept dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C28.dept int                  0      0      1  2
  quality_report.cluster_depth_consistency.clusters.C28.memb int                  0      0      1  2
  quality_report.cluster_depth_consistency.clusters.C28.pref int                  0      0      1  3
  quality_report.cluster_depth_consistency.clusters.C28.pref float                0      0      1  1.0
  quality_report.cluster_depth_consistency.clusters.C29      dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C29.dept dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C29.dept int                  0      0      1  2
  quality_report.cluster_depth_consistency.clusters.C29.memb int                  0      0      1  2
  quality_report.cluster_depth_consistency.clusters.C29.pref int                  0      0      1  2
  quality_report.cluster_depth_consistency.clusters.C29.pref float                0      0      1  1.0
  quality_report.cluster_depth_consistency.clusters.C30      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C30.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C30.dept int                  0      1      0  2
  quality_report.cluster_depth_consistency.clusters.C30.dept int                  0      1      0  3
  quality_report.cluster_depth_consistency.clusters.C30.memb int                  0      1      0  5
  quality_report.cluster_depth_consistency.clusters.C30.pref int                  0      1      0  3
  quality_report.cluster_depth_consistency.clusters.C30.pref float                0      1      0  0.6
  quality_report.cluster_depth_consistency.clusters.C31      dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C31.dept dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C31.dept int                  0      0      1  1
  quality_report.cluster_depth_consistency.clusters.C31.dept int                  1      0      0  1
  quality_report.cluster_depth_consistency.clusters.C31.memb int                  1      0      1  1
  quality_report.cluster_depth_consistency.clusters.C31.pref int                  1      0      1  4
  quality_report.cluster_depth_consistency.clusters.C31.pref float                1      0      1  1.0
  quality_report.cluster_depth_consistency.clusters.C32      dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C32.dept dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C32.dept int                  1      0      1  2
  quality_report.cluster_depth_consistency.clusters.C32.memb int                  1      0      1  2
  quality_report.cluster_depth_consistency.clusters.C32.pref int                  1      0      1  1
  quality_report.cluster_depth_consistency.clusters.C32.pref float                1      0      1  1.0
  quality_report.cluster_depth_consistency.clusters.C33      dict                 1      1      1  
  quality_report.cluster_depth_consistency.clusters.C33.dept dict                 1      1      1  
  quality_report.cluster_depth_consistency.clusters.C33.dept int                  1      0      1  2
  quality_report.cluster_depth_consistency.clusters.C33.dept int                  0      1      0  2
  quality_report.cluster_depth_consistency.clusters.C33.memb int                  1      1      1  2
  quality_report.cluster_depth_consistency.clusters.C33.pref int                  1      1      1  2
  quality_report.cluster_depth_consistency.clusters.C33.pref float                1      1      1  1.0
  quality_report.cluster_depth_consistency.clusters.C34      dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C34.dept dict                 0      0      1  
  quality_report.cluster_depth_consistency.clusters.C34.dept int                  0      0      1  1
  quality_report.cluster_depth_consistency.clusters.C34.memb int                  0      0      1  1
  quality_report.cluster_depth_consistency.clusters.C34.pref int                  0      0      1  2
  quality_report.cluster_depth_consistency.clusters.C34.pref float                0      0      1  1.0
  quality_report.cluster_depth_consistency.clusters.C36      dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C36.dept dict                 1      0      1  
  quality_report.cluster_depth_consistency.clusters.C36.dept int                  0      0      1  1
  quality_report.cluster_depth_consistency.clusters.C36.dept int                  1      0      0  1
  quality_report.cluster_depth_consistency.clusters.C36.memb int                  1      0      1  1
  quality_report.cluster_depth_consistency.clusters.C36.pref int                  1      0      1  4
  quality_report.cluster_depth_consistency.clusters.C36.pref float                1      0      1  1.0
  quality_report.cluster_depth_consistency.clusters.C37      dict                 1      1      0  
  quality_report.cluster_depth_consistency.clusters.C37.dept dict                 1      1      0  
  quality_report.cluster_depth_consistency.clusters.C37.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C37.dept int                  1      0      0  1
  quality_report.cluster_depth_consistency.clusters.C37.memb int                  1      1      0  1
  quality_report.cluster_depth_consistency.clusters.C37.pref int                  1      1      0  6
  quality_report.cluster_depth_consistency.clusters.C37.pref float                1      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C38      dict                 1      1      0  
  quality_report.cluster_depth_consistency.clusters.C38.dept dict                 1      1      0  
  quality_report.cluster_depth_consistency.clusters.C38.dept int                  1      1      0  1
  quality_report.cluster_depth_consistency.clusters.C38.memb int                  1      1      0  1
  quality_report.cluster_depth_consistency.clusters.C38.pref int                  1      1      0  2
  quality_report.cluster_depth_consistency.clusters.C38.pref float                1      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C39      dict                 1      1      1  
  quality_report.cluster_depth_consistency.clusters.C39.dept dict                 1      1      1  
  quality_report.cluster_depth_consistency.clusters.C39.dept int                  1      1      0  1
  quality_report.cluster_depth_consistency.clusters.C39.dept int                  0      0      1  1
  quality_report.cluster_depth_consistency.clusters.C39.memb int                  1      1      1  1
  quality_report.cluster_depth_consistency.clusters.C39.pref int                  1      1      1  2
  quality_report.cluster_depth_consistency.clusters.C39.pref float                1      1      1  1.0
  quality_report.cluster_depth_consistency.clusters.C40      dict                 1      1      1  
  quality_report.cluster_depth_consistency.clusters.C40.dept dict                 1      1      1  
  quality_report.cluster_depth_consistency.clusters.C40.dept int                  0      1      1  1
  quality_report.cluster_depth_consistency.clusters.C40.dept int                  1      0      0  1
  quality_report.cluster_depth_consistency.clusters.C40.memb int                  1      1      1  1
  quality_report.cluster_depth_consistency.clusters.C40.pref int                  1      1      1  3
  quality_report.cluster_depth_consistency.clusters.C40.pref float                1      1      1  1.0
  quality_report.cluster_depth_consistency.clusters.C41      dict                 1      1      0  
  quality_report.cluster_depth_consistency.clusters.C41.dept dict                 1      1      0  
  quality_report.cluster_depth_consistency.clusters.C41.dept int                  1      0      0  1
  quality_report.cluster_depth_consistency.clusters.C41.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C41.memb int                  1      1      0  1
  quality_report.cluster_depth_consistency.clusters.C41.pref int                  1      1      0  2
  quality_report.cluster_depth_consistency.clusters.C41.pref float                1      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C42      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C42.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C42.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C42.memb int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C42.pref int                  0      1      0  3
  quality_report.cluster_depth_consistency.clusters.C42.pref float                0      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C43      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C43.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C43.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C43.memb int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C43.pref int                  0      1      0  3
  quality_report.cluster_depth_consistency.clusters.C43.pref float                0      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C45      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C45.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C45.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C45.memb int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C45.pref int                  0      1      0  5
  quality_report.cluster_depth_consistency.clusters.C45.pref float                0      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C46      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C46.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C46.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C46.memb int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C46.pref int                  0      1      0  5
  quality_report.cluster_depth_consistency.clusters.C46.pref float                0      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C47      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C47.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C47.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C47.memb int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C47.pref int                  0      1      0  2
  quality_report.cluster_depth_consistency.clusters.C47.pref float                0      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C51      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C51.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C51.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C51.memb int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C51.pref int                  0      1      0  4
  quality_report.cluster_depth_consistency.clusters.C51.pref float                0      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C52      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C52.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C52.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C52.memb int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C52.pref int                  0      1      0  2
  quality_report.cluster_depth_consistency.clusters.C52.pref float                0      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C54      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C54.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C54.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C54.memb int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C54.pref int                  0      1      0  4
  quality_report.cluster_depth_consistency.clusters.C54.pref float                0      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C56      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C56.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C56.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C56.memb int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C56.pref int                  0      1      0  3
  quality_report.cluster_depth_consistency.clusters.C56.pref float                0      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C58      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C58.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C58.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C58.memb int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C58.pref int                  0      1      0  4
  quality_report.cluster_depth_consistency.clusters.C58.pref float                0      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C59      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C59.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C59.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C59.memb int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C59.pref int                  0      1      0  3
  quality_report.cluster_depth_consistency.clusters.C59.pref float                0      1      0  1.0
  quality_report.cluster_depth_consistency.clusters.C60      dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C60.dept dict                 0      1      0  
  quality_report.cluster_depth_consistency.clusters.C60.dept int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C60.memb int                  0      1      0  1
  quality_report.cluster_depth_consistency.clusters.C60.pref int                  0      1      0  3
  quality_report.cluster_depth_consistency.clusters.C60.pref float                0      1      0  1.0
  quality_report.cluster_depth_consistency.inconsistent_clus int                  1      1      1  5
  quality_report.depth_band_distribution                     dict                 1      1      1  
  quality_report.depth_band_distribution.annotation          int                  0      1      0  1
  quality_report.depth_band_distribution.body                int                  1      1      1  375
  quality_report.depth_band_distribution.peripheral          int                  1      1      1  36
  quality_report.depth_candidates                            dict                 1      1      1  
  quality_report.depth_candidates.blocks_with_multiple_candi int                  1      1      1  8
  quality_report.depth_candidates.candidate_count_distributi dict                 1      1      1  
  quality_report.depth_candidates.candidate_count_distributi int                  1      1      1  380
  quality_report.depth_candidates.candidate_count_distributi int                  1      1      1  31
  quality_report.depth_candidates.heading_jump_relaxation_ca int                  1      1      1  8
  quality_report.depth_constraints                           dict                 1      1      1  
  quality_report.depth_constraints.cluster_consistency_score float                1      1      1  1.0
  quality_report.depth_constraints.depth_changed_count       int                  1      1      1  0
  quality_report.depth_constraints.propagated_flow_block_cou int                  1      1      1  0
  quality_report.depth_constraints.relaxed_heading_count     int                  1      1      1  0
  quality_report.depth_constraints.unchanged_jump_count      int                  1      1      1  8
  quality_report.depth_distribution                          dict                 1      1      1  
  quality_report.depth_distribution.0                        int                  1      1      1  47
  quality_report.depth_distribution.1                        int                  1      1      1  43
  quality_report.depth_distribution.10                       int                  0      1      0  10
  quality_report.depth_distribution.2                        int                  1      1      1  53
  quality_report.depth_distribution.3                        int                  1      1      1  117
  quality_report.depth_distribution.4                        int                  1      1      1  85
  quality_report.depth_distribution.5                        int                  1      1      1  35
  quality_report.depth_distribution.6                        int                  1      1      0  5
  quality_report.depth_distribution.7                        int                  1      1      0  18
  quality_report.depth_distribution.8                        int                  1      0      0  8
  quality_report.depth_distribution.9                        int                  0      1      0  6
  quality_report.document                                    dict                 1      1      1  
  quality_report.document.block_count                        int                  1      1      1  411
  quality_report.floating_object_stats                       dict                 1      1      1  
  quality_report.floating_object_stats.floating_anchor_ambig int                  1      1      1  0
  quality_report.floating_object_stats.floating_anchor_resol int                  1      1      1  8
  quality_report.floating_object_stats.floating_anchor_unres int                  1      1      1  0
  quality_report.floating_object_stats.floating_block_count  int                  1      1      1  8
  quality_report.floating_object_stats.floating_block_type_d dict                 1      1      1  
  quality_report.floating_object_stats.floating_block_type_d int                  1      1      0  4
  quality_report.floating_object_stats.floating_block_type_d int                  0      1      0  4
  quality_report.floating_object_stats.floating_block_type_d int                  1      1      1  4
  quality_report.floating_object_stats.floating_object_count int                  1      1      1  8
  quality_report.floating_object_stats.floating_order_change int                  1      1      1  0
  quality_report.floating_object_stats.unresolved_count      int                  1      1      1  0
  quality_report.native_numbering_stats                      dict                 1      1      1  
  quality_report.native_numbering_stats.bullet_block_count   int                  1      1      1  0
  quality_report.native_numbering_stats.native_numbering_seq int                  1      1      1  0
  quality_report.native_numbering_stats.numbering_block_coun int                  1      1      1  0
  quality_report.native_numbering_stats.numbering_level_dist dict                 1      1      1  
  quality_report.native_numbering_stats.numbering_level_dist int                  0      1      1  248
  quality_report.orphan_anchor_stats                         dict                 1      1      1  
  quality_report.orphan_anchor_stats.anchored_caption_count  int                  1      1      1  0
  quality_report.orphan_anchor_stats.anchored_footnote_count int                  1      1      1  0
  quality_report.orphan_anchor_stats.caption_block_count     int                  1      1      1  0
  quality_report.orphan_anchor_stats.footnote_block_count    int                  1      1      1  0
  quality_report.orphan_anchor_stats.orphan_caption_uncertai int                  1      1      1  0
  quality_report.orphan_anchor_stats.orphan_caption_unresolv int                  1      1      1  0
  quality_report.orphan_anchor_stats.orphan_footnote_uncerta int                  1      1      1  0
  quality_report.orphan_anchor_stats.orphan_footnote_unresol int                  1      1      1  0
  quality_report.peripheral_stats                            dict                 1      1      1  
  quality_report.peripheral_stats.page_footer_count          int                  1      1      1  4
  quality_report.semantic_role_distribution                  dict                 1      1      1  
  quality_report.semantic_role_distribution.body_text        int                  1      1      1  58
  quality_report.semantic_role_distribution.caption          int                  0      1      0  1
  quality_report.semantic_role_distribution.decorative_shape int                  0      1      0  1
  quality_report.semantic_role_distribution.document_control int                  1      1      1  32
  quality_report.semantic_role_distribution.empty_paragraph  int                  1      1      1  135
  quality_report.semantic_role_distribution.figure           int                  1      1      1  39
  quality_report.semantic_role_distribution.list_item        int                  0      1      1  248
  quality_report.semantic_role_distribution.page_footer      int                  1      1      1  4
  quality_report.semantic_role_distribution.page_header      int                  0      0      1  2
  quality_report.semantic_role_distribution.section_heading  int                  1      1      1  58
  quality_report.semantic_role_distribution.table            int                  1      1      1  85
  quality_report.severity_distribution                       dict                 1      1      1  
  quality_report.severity_distribution.info                  int                  1      1      1  53
  quality_report.severity_distribution.warning               int                  1      1      1  107
  quality_report.table_hierarchy_ref                         dict                 1      1      1  
  quality_report.table_hierarchy_ref.all_table_hierarchy_sta dict                 1      1      1  
  quality_report.table_hierarchy_ref.all_table_hierarchy_sta int                  1      1      1  200
  quality_report.table_hierarchy_ref.all_table_hierarchy_sta dict                 1      1      1  
  quality_report.table_hierarchy_ref.all_table_hierarchy_sta int                  1      1      1  169
  quality_report.table_hierarchy_ref.all_table_hierarchy_sta int                  1      1      1  2
  quality_report.table_hierarchy_ref.all_table_hierarchy_sta int                  1      1      1  29
  quality_report.table_hierarchy_ref.all_table_hierarchy_sta dict                 1      1      1  
  quality_report.table_hierarchy_ref.all_table_hierarchy_sta int                  1      1      1  170
  quality_report.table_hierarchy_ref.all_table_hierarchy_sta int                  1      1      1  5
  quality_report.table_hierarchy_ref.all_table_hierarchy_sta int                  1      1      1  25
  quality_report.table_hierarchy_ref.top_level_block_stats   dict                 1      1      1  
  quality_report.table_hierarchy_ref.top_level_block_stats.m dict                 1      1      1  
  quality_report.table_hierarchy_ref.top_level_block_stats.m int                  1      1      1  85
  quality_report.table_hierarchy_ref.top_level_block_stats.r dict                 1      1      1  
  quality_report.table_hierarchy_ref.top_level_block_stats.r int                  1      1      1  78
  quality_report.table_hierarchy_ref.top_level_block_stats.r int                  1      1      1  1
  quality_report.table_hierarchy_ref.top_level_block_stats.r int                  1      1      1  6
  quality_report.table_hierarchy_ref.top_level_block_stats.t int                  1      1      1  85
  quality_report.table_hierarchy_ref.top_level_block_stats.t dict                 1      1      1  
  quality_report.table_hierarchy_ref.top_level_block_stats.t int                  1      1      1  51
  quality_report.table_hierarchy_ref.top_level_block_stats.t int                  1      1      1  50
  quality_report.table_hierarchy_ref.top_level_block_stats.t int                  1      1      1  45
  quality_report.table_hierarchy_ref.top_level_block_stats.t int                  1      1      1  1
  quality_report.table_hierarchy_ref.top_level_block_stats.t dict                 1      1      1  
  quality_report.table_hierarchy_ref.top_level_block_stats.t int                  1      1      1  57
  quality_report.table_hierarchy_ref.top_level_block_stats.t int                  1      1      1  3
  quality_report.table_hierarchy_ref.top_level_block_stats.t int                  1      1      1  25
  quality_report.table_internal_ref_stats                    dict                 1      1      1  
  quality_report.table_internal_ref_stats.cell_group_count   int                  1      1      1  2150
  quality_report.table_internal_ref_stats.duplicate_internal int                  1      1      1  0
  quality_report.table_internal_ref_stats.max_absolute_depth int                  1      1      1  14
  quality_report.table_internal_ref_stats.max_local_depth    int                  1      1      1  9
  quality_report.table_internal_ref_stats.missing_parent_ref int                  1      1      1  0
  quality_report.table_internal_ref_stats.nested_table_ref_c int                  1      1      1  115
  quality_report.table_internal_ref_stats.row_group_count    int                  1      1      1  697
  quality_report.table_internal_ref_stats.table_internal_blo int                  1      1      1  5072
  quality_report.table_internal_ref_stats.text_block_count   int                  1      1      1  1835
  quality_report.table_internal_ref_stats.top_level_tables_w int                  1      1      1  45
  quality_report.table_internal_validation                   dict                 1      1      1  
  quality_report.table_internal_validation.cell_group_count  int                  1      1      1  2150
  quality_report.table_internal_validation.cell_group_count_ int                  1      1      1  0
  quality_report.table_internal_validation.duplicate_interna int                  1      1      1  0
  quality_report.table_internal_validation.expected_recursiv int                  1      1      1  2150
  quality_report.table_internal_validation.expected_recursiv int                  1      1      1  115
  quality_report.table_internal_validation.expected_recursiv int                  1      1      1  267
  quality_report.table_internal_validation.invalid_cell_span int                  1      1      1  0
  quality_report.table_internal_validation.invalid_internal_ int                  1      1      1  0
  quality_report.table_internal_validation.invalid_parent_re int                  1      1      1  0
  quality_report.table_internal_validation.max_absolute_dept int                  1      1      1  14
  quality_report.table_internal_validation.max_local_depth   int                  1      1      1  9
  quality_report.table_internal_validation.missing_cell_addr int                  1      1      1  0
  quality_report.table_internal_validation.missing_parent_re int                  1      1      1  0
  quality_report.table_internal_validation.missing_root_tabl int                  1      1      1  0
  quality_report.table_internal_validation.missing_source_bl int                  1      1      1  0
  quality_report.table_internal_validation.missing_source_ta int                  1      1      1  0
  quality_report.table_internal_validation.nested_ref_count_ int                  1      1      1  0
  quality_report.table_internal_validation.nested_table_pres int                  1      1      1  0
  quality_report.table_internal_validation.nested_table_ref_ int                  1      1      1  115
  quality_report.table_internal_validation.object_ref_count_ int                  1      1      1  0
  quality_report.table_internal_validation.possible_nested_t int                  1      1      1  0
  quality_report.table_internal_validation.record_status_mis int                  1      1      1  0
  quality_report.table_internal_validation.record_status_nul int                  1      1      1  0
  quality_report.table_internal_validation.row_group_count   int                  1      1      1  697
  quality_report.table_internal_validation.table_caption_cou int                  1      1      1  6
  quality_report.table_internal_validation.table_control_cou int                  1      1      1  2
  quality_report.table_internal_validation.table_internal_bl int                  1      1      1  5072
  quality_report.table_internal_validation.table_object_ref_ int                  1      1      1  267
  quality_report.table_internal_validation.text_block_count  int                  1      1      1  1835
  quality_report.table_internal_validation.top_level_tables_ int                  1      1      1  85
  quality_report.table_internal_validation.top_level_tables_ int                  1      1      1  45
  quality_report.table_internal_validation.validation_passed bool                 1      1      1  True
  quality_report.warning_code_distribution                   dict                 1      1      1  
  quality_report.warning_code_distribution.cluster_depth_inc int                  1      1      1  5
  quality_report.warning_code_distribution.low_record_confid int                  1      1      1  51
  quality_report.warning_code_distribution.missing_header_ro int                  1      1      1  50
  quality_report.warning_code_distribution.nested_table_pres int                  1      1      1  45
  quality_report.warning_code_distribution.raw_only_table    int                  1      1      1  1
  quality_report.warning_code_distribution.unchanged_depth_j int                  1      1      1  8

====================================================================================================
문서마다 출현이 갈리는 필드 356개
====================================================================================================
  blocks_document.blocks[].depth_correction.carried_over_scope             성과평가
  blocks_document.blocks[].depth_correction.indent_key                     성과평가
  blocks_document.blocks[].depth_correction.marker_class                   성과평가
  blocks_document.blocks[].depth_correction.ordinal_family                 성과평가
  blocks_document.blocks[].depth_correction.ordinal_value                  성과평가
  blocks_document.blocks[].line_features.line_segments[].char_pr_refs      수정계획
  blocks_document.blocks[].line_features.line_segments[].line_index        수정계획
  blocks_document.blocks[].line_features.line_segments[].text              수정계획
  blocks_document.blocks[].structure_features.child_object_summary.ellipse 연차평가
  blocks_document.blocks[].structure_features.child_object_summary.pic     수정계획
  blocks_document.blocks[].style_features.auto_label.bullet_id             수정계획, 연차평가
  blocks_document.blocks[].style_features.auto_label.is_private_use        수정계획, 연차평가
  blocks_document.blocks[].style_features.auto_label.label_kind            수정계획, 연차평가
  blocks_document.blocks[].style_features.auto_label.level                 수정계획, 연차평가
  blocks_document.blocks[].style_features.auto_label.text                  수정계획, 연차평가
  blocks_document.quality.block_type_counts.caption                        수정계획
  blocks_document.quality.block_type_counts.header                         연차평가
  blocks_document.quality.depth_update_log[].affected_by_heading_block_id  수정계획
  blocks_document.quality.depth_update_log[].block_id                      수정계획
  blocks_document.quality.depth_update_log[].new_depth                     수정계획
  blocks_document.quality.depth_update_log[].old_depth                     수정계획
  blocks_document.quality.depth_update_log[].reason                        수정계획
  blocks_document.quality.nested_control_skipped.by_container.drawText/aut 성과평가, 수정계획
  blocks_document.quality.nested_control_skipped.by_container.drawText/col 성과평가, 수정계획
  blocks_document.quality.nested_control_skipped.by_container.drawText/pag 연차평가
  blocks_document.quality.nested_control_skipped.by_container.tbl/autoNum  연차평가
  blocks_document.quality.nested_control_skipped.by_container.tbl/header   연차평가
  blocks_document.quality.nested_control_skipped.by_container.tbl/newNum   성과평가, 수정계획
  blocks_document.quality.nested_control_skipped.by_container.tbl/pageHidi 성과평가
  blocks_document.quality.semantic_role_counts.caption                     수정계획
  blocks_document.quality.semantic_role_counts.decorative_shape_candidate  수정계획
  blocks_document.quality.semantic_role_counts.list_item                   수정계획, 연차평가
  blocks_document.quality.semantic_role_counts.page_header                 연차평가
  blocks_document.quality.toc_depth0_anchor.entry_count_by_level.2         성과평가, 수정계획
  blocks_document.quality.toc_depth0_anchor.entry_count_by_level.3         수정계획
  blocks_document.quality.toc_depth0_anchor.matched_block_ids_by_level.2   성과평가, 수정계획
  blocks_document.quality.toc_depth0_anchor.matched_block_ids_by_level.3   수정계획
  blocks_document.quality.toc_depth0_anchor.matched_count_by_level.2       성과평가, 수정계획
  blocks_document.quality.toc_depth0_anchor.matched_count_by_level.3       수정계획
  quality_report.block_type_distribution.caption                           수정계획
  quality_report.block_type_distribution.header                            연차평가
  quality_report.cluster_depth_consistency.clusters.C05                    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C05.depth_distribution 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C05.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C05.depth_distribution 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C05.depth_distribution 성과평가
  quality_report.cluster_depth_consistency.clusters.C05.depth_distribution 성과평가
  quality_report.cluster_depth_consistency.clusters.C05.member_count       성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C05.preferred_depth    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C05.preferred_depth_ra 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C07.depth_distribution 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C07.depth_distribution 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C08                    성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C08.depth_distribution 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C08.depth_distribution 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C08.depth_distribution 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C08.depth_distribution 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C08.member_count       성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C08.preferred_depth    성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C08.preferred_depth_ra 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C10                    수정계획
  quality_report.cluster_depth_consistency.clusters.C10.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C10.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C10.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C10.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C10.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C11                    수정계획
  quality_report.cluster_depth_consistency.clusters.C11.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C11.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C11.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C11.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C11.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C11.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C11.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C11.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C13                    연차평가
  quality_report.cluster_depth_consistency.clusters.C13.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C13.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C13.member_count       연차평가
  quality_report.cluster_depth_consistency.clusters.C13.preferred_depth    연차평가
  quality_report.cluster_depth_consistency.clusters.C13.preferred_depth_ra 연차평가
  quality_report.cluster_depth_consistency.clusters.C15                    연차평가
  quality_report.cluster_depth_consistency.clusters.C15.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C15.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C15.member_count       연차평가
  quality_report.cluster_depth_consistency.clusters.C15.preferred_depth    연차평가
  quality_report.cluster_depth_consistency.clusters.C15.preferred_depth_ra 연차평가
  quality_report.cluster_depth_consistency.clusters.C16                    수정계획
  quality_report.cluster_depth_consistency.clusters.C16.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C16.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C16.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C16.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C16.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C16.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C16.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C17                    연차평가
  quality_report.cluster_depth_consistency.clusters.C17.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C17.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C17.member_count       연차평가
  quality_report.cluster_depth_consistency.clusters.C17.preferred_depth    연차평가
  quality_report.cluster_depth_consistency.clusters.C17.preferred_depth_ra 연차평가
  quality_report.cluster_depth_consistency.clusters.C19                    연차평가
  quality_report.cluster_depth_consistency.clusters.C19.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C19.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C19.member_count       연차평가
  quality_report.cluster_depth_consistency.clusters.C19.preferred_depth    연차평가
  quality_report.cluster_depth_consistency.clusters.C19.preferred_depth_ra 연차평가
  quality_report.cluster_depth_consistency.clusters.C20                    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C20.depth_distribution 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C20.depth_distribution 성과평가
  quality_report.cluster_depth_consistency.clusters.C20.depth_distribution 성과평가
  quality_report.cluster_depth_consistency.clusters.C20.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C20.member_count       성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C20.preferred_depth    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C20.preferred_depth_ra 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C21                    연차평가
  quality_report.cluster_depth_consistency.clusters.C21.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C21.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C21.member_count       연차평가
  quality_report.cluster_depth_consistency.clusters.C21.preferred_depth    연차평가
  quality_report.cluster_depth_consistency.clusters.C21.preferred_depth_ra 연차평가
  quality_report.cluster_depth_consistency.clusters.C22                    수정계획, 연차평가
  quality_report.cluster_depth_consistency.clusters.C22.depth_distribution 수정계획, 연차평가
  quality_report.cluster_depth_consistency.clusters.C22.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C22.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C22.member_count       수정계획, 연차평가
  quality_report.cluster_depth_consistency.clusters.C22.preferred_depth    수정계획, 연차평가
  quality_report.cluster_depth_consistency.clusters.C22.preferred_depth_ra 수정계획, 연차평가
  quality_report.cluster_depth_consistency.clusters.C23                    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C23.depth_distribution 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C23.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C23.depth_distribution 성과평가
  quality_report.cluster_depth_consistency.clusters.C23.member_count       성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C23.preferred_depth    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C23.preferred_depth_ra 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C26                    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C26.depth_distribution 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C26.depth_distribution 성과평가
  quality_report.cluster_depth_consistency.clusters.C26.depth_distribution 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C26.member_count       성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C26.preferred_depth    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C26.preferred_depth_ra 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C27                    연차평가
  quality_report.cluster_depth_consistency.clusters.C27.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C27.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C27.member_count       연차평가
  quality_report.cluster_depth_consistency.clusters.C27.preferred_depth    연차평가
  quality_report.cluster_depth_consistency.clusters.C27.preferred_depth_ra 연차평가
  quality_report.cluster_depth_consistency.clusters.C28                    연차평가
  quality_report.cluster_depth_consistency.clusters.C28.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C28.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C28.member_count       연차평가
  quality_report.cluster_depth_consistency.clusters.C28.preferred_depth    연차평가
  quality_report.cluster_depth_consistency.clusters.C28.preferred_depth_ra 연차평가
  quality_report.cluster_depth_consistency.clusters.C29                    연차평가
  quality_report.cluster_depth_consistency.clusters.C29.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C29.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C29.member_count       연차평가
  quality_report.cluster_depth_consistency.clusters.C29.preferred_depth    연차평가
  quality_report.cluster_depth_consistency.clusters.C29.preferred_depth_ra 연차평가
  quality_report.cluster_depth_consistency.clusters.C30                    수정계획
  quality_report.cluster_depth_consistency.clusters.C30.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C30.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C30.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C30.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C30.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C30.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C31                    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C31.depth_distribution 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C31.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C31.depth_distribution 성과평가
  quality_report.cluster_depth_consistency.clusters.C31.member_count       성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C31.preferred_depth    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C31.preferred_depth_ra 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C32                    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C32.depth_distribution 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C32.depth_distribution 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C32.member_count       성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C32.preferred_depth    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C32.preferred_depth_ra 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C33.depth_distribution 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C33.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C34                    연차평가
  quality_report.cluster_depth_consistency.clusters.C34.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C34.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C34.member_count       연차평가
  quality_report.cluster_depth_consistency.clusters.C34.preferred_depth    연차평가
  quality_report.cluster_depth_consistency.clusters.C34.preferred_depth_ra 연차평가
  quality_report.cluster_depth_consistency.clusters.C36                    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C36.depth_distribution 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C36.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C36.depth_distribution 성과평가
  quality_report.cluster_depth_consistency.clusters.C36.member_count       성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C36.preferred_depth    성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C36.preferred_depth_ra 성과평가, 연차평가
  quality_report.cluster_depth_consistency.clusters.C37                    성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C37.depth_distribution 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C37.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C37.depth_distribution 성과평가
  quality_report.cluster_depth_consistency.clusters.C37.member_count       성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C37.preferred_depth    성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C37.preferred_depth_ra 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C38                    성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C38.depth_distribution 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C38.depth_distribution 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C38.member_count       성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C38.preferred_depth    성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C38.preferred_depth_ra 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C39.depth_distribution 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C39.depth_distribution 연차평가
  quality_report.cluster_depth_consistency.clusters.C40.depth_distribution 수정계획, 연차평가
  quality_report.cluster_depth_consistency.clusters.C40.depth_distribution 성과평가
  quality_report.cluster_depth_consistency.clusters.C41                    성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C41.depth_distribution 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C41.depth_distribution 성과평가
  quality_report.cluster_depth_consistency.clusters.C41.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C41.member_count       성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C41.preferred_depth    성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C41.preferred_depth_ra 성과평가, 수정계획
  quality_report.cluster_depth_consistency.clusters.C42                    수정계획
  quality_report.cluster_depth_consistency.clusters.C42.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C42.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C42.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C42.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C42.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C43                    수정계획
  quality_report.cluster_depth_consistency.clusters.C43.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C43.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C43.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C43.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C43.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C45                    수정계획
  quality_report.cluster_depth_consistency.clusters.C45.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C45.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C45.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C45.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C45.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C46                    수정계획
  quality_report.cluster_depth_consistency.clusters.C46.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C46.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C46.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C46.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C46.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C47                    수정계획
  quality_report.cluster_depth_consistency.clusters.C47.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C47.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C47.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C47.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C47.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C51                    수정계획
  quality_report.cluster_depth_consistency.clusters.C51.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C51.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C51.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C51.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C51.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C52                    수정계획
  quality_report.cluster_depth_consistency.clusters.C52.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C52.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C52.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C52.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C52.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C54                    수정계획
  quality_report.cluster_depth_consistency.clusters.C54.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C54.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C54.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C54.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C54.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C56                    수정계획
  quality_report.cluster_depth_consistency.clusters.C56.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C56.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C56.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C56.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C56.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C58                    수정계획
  quality_report.cluster_depth_consistency.clusters.C58.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C58.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C58.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C58.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C58.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C59                    수정계획
  quality_report.cluster_depth_consistency.clusters.C59.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C59.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C59.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C59.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C59.preferred_depth_ra 수정계획
  quality_report.cluster_depth_consistency.clusters.C60                    수정계획
  quality_report.cluster_depth_consistency.clusters.C60.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C60.depth_distribution 수정계획
  quality_report.cluster_depth_consistency.clusters.C60.member_count       수정계획
  quality_report.cluster_depth_consistency.clusters.C60.preferred_depth    수정계획
  quality_report.cluster_depth_consistency.clusters.C60.preferred_depth_ra 수정계획
  quality_report.depth_band_distribution.annotation                        수정계획
  quality_report.depth_distribution.10                                     수정계획
  quality_report.depth_distribution.6                                      성과평가, 수정계획
  quality_report.depth_distribution.7                                      성과평가, 수정계획
  quality_report.depth_distribution.8                                      성과평가
  quality_report.depth_distribution.9                                      수정계획
  quality_report.floating_object_stats.floating_block_type_distribution.im 성과평가, 수정계획
  quality_report.floating_object_stats.floating_block_type_distribution.sh 수정계획
  quality_report.native_numbering_stats.numbering_level_distribution.0     수정계획, 연차평가
  quality_report.semantic_role_distribution.caption                        수정계획
  quality_report.semantic_role_distribution.decorative_shape_candidate     수정계획
  quality_report.semantic_role_distribution.list_item                      수정계획, 연차평가
  quality_report.semantic_role_distribution.page_header                    연차평가
  summary.error_count                                                      성과평가
  summary.header.bullet_count                                              수정계획, 연차평가
  summary.header.heading_level_count                                       성과평가
  summary.header.numbering_count                                           수정계획, 연차평가
  summary.header.style_name_count                                          성과평가
  summary.header.style_to_char_pr_count                                    성과평가
  summary.header.style_to_para_pr_count                                    성과평가
  summary.header_file_path                                                 성과평가
  summary.header_reference_validation                                      성과평가
  summary.header_reference_validation.missing_char_pr_ref_table_count      성과평가
  summary.header_reference_validation.missing_para_pr_ref_table_count      성과평가
  summary.header_reference_validation.missing_style_ref_table_count        성과평가
  summary.header_reference_validation.tables_with_missing_char_pr_ref      성과평가
  summary.header_reference_validation.tables_with_missing_para_pr_ref      성과평가
  summary.header_reference_validation.tables_with_missing_style_ref        성과평가
  summary.image_dir_path                                                   성과평가
  summary.invalid_table_count                                              성과평가
  summary.invalid_table_ids                                                성과평가
  summary.total_issue_count                                                성과평가
  summary.warning_count                                                    성과평가
  tables.analyzed[].hierarchy.structured_records[].row_headers.(단위 : 백만원,  연차평가
  tables.analyzed[].hierarchy.structured_records[].row_headers.As-Is       성과평가
  tables.analyzed[].hierarchy.structured_records[].row_headers.‘           연차평가
  tables.analyzed[].hierarchy.structured_records[].row_headers.구분          성과평가, 수정계획
  tables.analyzed[].hierarchy.structured_records[].row_headers.내용          성과평가
  tables.analyzed[].hierarchy.structured_records[].row_headers.단계          성과평가
  tables.analyzed[].hierarchy.structured_records[].row_headers.단과대학        성과평가, 수정계획
  tables.analyzed[].hierarchy.structured_records[].row_headers.성과지표        연차평가
  tables.analyzed[].hierarchy.structured_records[].row_headers.역량          성과평가
  tables.analyzed[].hierarchy.structured_records[].row_headers.영역          수정계획
  tables.analyzed[].hierarchy.structured_records[].row_headers.운영 내용       성과평가
  tables.analyzed[].hierarchy.structured_records[].row_headers.조직 구분       수정계획
  tables.analyzed[].hierarchy.structured_records[].row_headers.주요 대회명      성과평가
  tables.analyzed[].hierarchy.structured_records[].row_headers.주요 성과지표 교육혁 수정계획
  tables.analyzed[].hierarchy.structured_records[].row_headers.주요 성과지표 전공교 수정계획
  tables.analyzed[].hierarchy.structured_records[].row_headers.팀명          성과평가
  tables.analyzed[].hierarchy.structured_records[].row_headers.프로그램        성과평가
  tables.analyzed[].hierarchy.structured_records[].row_headers.하위지표 전공 교육  수정계획
  tables.analyzed[].hierarchy.structured_records[].row_headers.학과          수정계획
  tables.analyzed[].hierarchy.structured_records[].row_headers.회계연도        수정계획
  tables.analyzed[].preprocess.cells[].objects.captions[].binary_item_id_r 성과평가
  tables.analyzed[].preprocess.cells[].objects.captions[].caption_id       성과평가
  tables.analyzed[].preprocess.cells[].objects.captions[].parent_object_ty 성과평가
  tables.analyzed[].preprocess.cells[].objects.captions[].raw_attrs        성과평가
  tables.analyzed[].preprocess.cells[].objects.captions[].raw_attrs.fullSz 성과평가
  tables.analyzed[].preprocess.cells[].objects.captions[].raw_attrs.gap    성과평가
  tables.analyzed[].preprocess.cells[].objects.captions[].raw_attrs.lastWi 성과평가
  tables.analyzed[].preprocess.cells[].objects.captions[].raw_attrs.side   성과평가
  tables.analyzed[].preprocess.cells[].objects.captions[].raw_attrs.width  성과평가
  tables.analyzed[].preprocess.cells[].objects.captions[].text             성과평가
  warnings[].evidence.internal_block_id                                    연차평가
  warnings[].evidence.source_block_id                                      연차평가

====================================================================================================
항상 비어 있는 필드 21개
====================================================================================================
  blocks_document.blocks[].anchor_resolution.reason
  blocks_document.blocks[].layout_position.bounding_box_estimate
  blocks_document.blocks[].layout_position.page_number_estimate
  blocks_document.blocks[].style_features.heading_level_native
  blocks_document.blocks[].table_hierarchy_ref.nesting.parent_cell_id
  blocks_document.blocks[].table_hierarchy_ref.nesting.parent_table_id
  blocks_document.quality.unresolved_blocks
  summary.header_reference_validation.tables_with_missing_char_pr_ref
  summary.header_reference_validation.tables_with_missing_para_pr_ref
  summary.header_reference_validation.tables_with_missing_style_ref
  summary.invalid_table_ids
  tables.analyzed[].grid.issues
  tables.analyzed[].hierarchy.caption_or_note_cells
  tables.analyzed[].preprocess.candidates.note_candidate
  tables.analyzed[].preprocess.candidates.source_candidate
  tables.analyzed[].preprocess.validation.header_border_row_indices
  tables.analyzed[].preprocess.validation.issues
  tables.body_linking[].candidates.note_candidate
  tables.body_linking[].candidates.source_candidate
  tables.body_linking[].hierarchy.caption_or_note_cells
  warnings[].evidence.source_block_id
```

# 섹션 간 참조 무결성

```
============================================================================================
성과평가
============================================================================================
  식별자: block_id 411 / table_id 200 / cell_id 2150 / internal_block_id 5072
    [OK ] blocks[].table_hierarchy_ref.table_id  ->  tables.analyzed[].table_id         85건 / 미아 0
    [OK ] internal_blocks[].source_block_id  ->  blocks[].block_id                    5072건 / 미아 0
    [OK ] internal_blocks[].source_table_id  ->  tables.analyzed[].table_id           5072건 / 미아 0
    [OK ] internal_blocks[].root_table_id  ->  tables.analyzed[].table_id             5072건 / 미아 0
    [OK ] internal_blocks[].parent_internal_block_id  ->  internal_block_id           4747건 / 미아 0
    [OK ] internal_blocks[type=table_cell_group].id  ->  preprocess.cells[].cell_id   2150건 / 미아 0
    [OK ] table_internal_blocks.tables[].source_block_id  ->  blocks[].block_id         85건 / 미아 0
    [OK ] tables.analyzed[].parent_table_id  ->  table_id                              115건 / 미아 0
    [OK ] tables.analyzed[].parent_cell_id  ->  cells[].cell_id                        115건 / 미아 0
    [OK ] warnings[].block_id  ->  blocks[].block_id                                   160건 / 미아 0
    [OK ] quality.toc_depth0_anchor.matched_block_ids  ->  blocks[].block_id             9건 / 미아 0
    [OK ] quality.toc_depth0_anchor.toc_source_table_ids  ->  table_id                   1건 / 미아 0

============================================================================================
수정계획
============================================================================================
  식별자: block_id 1110 / table_id 327 / cell_id 5887 / internal_block_id 13117
    [OK ] blocks[].table_hierarchy_ref.table_id  ->  tables.analyzed[].table_id        213건 / 미아 0
    [OK ] internal_blocks[].source_block_id  ->  blocks[].block_id                   13117건 / 미아 0
    [OK ] internal_blocks[].source_table_id  ->  tables.analyzed[].table_id          13117건 / 미아 0
    [OK ] internal_blocks[].root_table_id  ->  tables.analyzed[].table_id            13117건 / 미아 0
    [OK ] internal_blocks[].parent_internal_block_id  ->  internal_block_id          11751건 / 미아 0
    [OK ] internal_blocks[type=table_cell_group].id  ->  preprocess.cells[].cell_id   5887건 / 미아 0
    [OK ] table_internal_blocks.tables[].source_block_id  ->  blocks[].block_id        213건 / 미아 0
    [OK ] tables.analyzed[].parent_table_id  ->  table_id                              114건 / 미아 0
    [OK ] tables.analyzed[].parent_cell_id  ->  cells[].cell_id                        114건 / 미아 0
    [OK ] warnings[].block_id  ->  blocks[].block_id                                   245건 / 미아 0
    [OK ] quality.toc_depth0_anchor.matched_block_ids  ->  blocks[].block_id            12건 / 미아 0
    [OK ] quality.toc_depth0_anchor.toc_source_table_ids  ->  table_id                   1건 / 미아 0

============================================================================================
연차평가
============================================================================================
  식별자: block_id 605 / table_id 201 / cell_id 3174 / internal_block_id 6263
    [OK ] blocks[].table_hierarchy_ref.table_id  ->  tables.analyzed[].table_id        117건 / 미아 0
    [OK ] internal_blocks[].source_block_id  ->  blocks[].block_id                    6250건 / 미아 0
    [OK ] internal_blocks[].source_table_id  ->  tables.analyzed[].table_id           6263건 / 미아 0
    [OK ] internal_blocks[].root_table_id  ->  tables.analyzed[].table_id             6263건 / 미아 0
    [OK ] internal_blocks[].parent_internal_block_id  ->  internal_block_id           5549건 / 미아 0
    [OK ] internal_blocks[type=table_cell_group].id  ->  preprocess.cells[].cell_id   3174건 / 미아 0
    [OK ] table_internal_blocks.tables[].source_block_id  ->  blocks[].block_id        117건 / 미아 0
    [OK ] tables.analyzed[].parent_table_id  ->  table_id                               80건 / 미아 0
    [OK ] tables.analyzed[].parent_cell_id  ->  cells[].cell_id                         80건 / 미아 0
    [OK ] warnings[].block_id  ->  blocks[].block_id                                   181건 / 미아 0
    [OK ] quality.toc_depth0_anchor.matched_block_ids  ->  blocks[].block_id             8건 / 미아 0
    [OK ] quality.toc_depth0_anchor.toc_source_table_ids  ->  table_id                   1건 / 미아 0

```
