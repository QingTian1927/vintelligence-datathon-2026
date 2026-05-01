# Milestone 2 - MCQ Computation Report

## Method
- All answers are computed directly from provided competition CSV files.
- No external data is used.
- Ambiguity handling is documented in the detail column, especially for Q7.
- Values are reported at 4-decimal precision.

## Final Answers
- Q1: option C | value=144.0 | metric=median_inter_order_gap_days | detail=num_gaps=556699 | choices: A=30, B=90, C=144, D=365
- Q10: option C | value=24446.6544 | metric=highest_avg_payment_value_by_installment_plan | detail=6 | choices: A=1, B=3, C=6, D=12 installments
- Q2: option D | value=0.3134 | metric=highest_avg_margin_segment | detail=Standard | choices: A=Premium, B=Performance, C=Activewear, D=Standard
- Q3: option B | value=7626.0 | metric=most_common_streetwear_return_reason | detail=wrong_size | choices: A=defective, B=wrong_size, C=changed_mind, D=not_as_described
- Q4: option C | value=0.0045 | metric=lowest_avg_bounce_source | detail=email_campaign | choices: A=organic_search, B=paid_search, C=email_campaign, D=social_media
- Q5: option C | value=38.6635 | metric=pct_rows_with_promo_id | detail=promo_id is not null | choices: A=12%, B=25%, C=39%, D=54%
- Q6: option A | value=5.4069 | metric=highest_avg_orders_per_customer_by_age_group | detail=strict_top=55+; alt_top=55+ | choices: A=55+, B=25-, C=35-, D=45-
- Q7: option C | value=7291150819.12 | metric=highest_total_revenue_region_ambiguous_definition | detail=strict ambiguous; pay_top=East; item_top=East; chose consensus | choices: A=West, B=Central, C=East, D=approximately equal
- Q8: option A | value=28452.0 | metric=most_used_payment_method_in_cancelled_orders | detail=credit_card | choices: A=credit_card, B=cod, C=paypal, D=bank_transfer
- Q9: option A | value=0.0565 | metric=highest_return_rate_by_size | detail=S | choices: A=S, B=M, C=L, D=XL

## Output Files
- outputs/tables/m2_mcq_summary_primary.csv
- outputs/tables/m2_final_answers.csv
- outputs/tables/m2_q2_segment_margin.csv
- outputs/tables/m2_q3_streetwear_return_reason.csv
- outputs/tables/m2_q4_bounce_by_source.csv
- outputs/tables/m2_q6_age_group_strict.csv
- outputs/tables/m2_q6_age_group_alt_active_only.csv
- outputs/tables/m2_q7_region_revenue_alternatives.csv
- outputs/tables/m2_q8_cancelled_payment_method.csv
- outputs/tables/m2_q9_return_rate_by_size.csv
- outputs/tables/m2_q10_installment_avg_payment.csv