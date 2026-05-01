# Báo cáo Vòng Sơ Loại DATATHON 2026

**Đội thi:** Shosa Degree  
**Chủ đề:** Dự báo doanh thu và phân tích EDA cho doanh nghiệp thời trang thương mại điện tử  
**Ngôn ngữ:** Tiếng Việt  
**Nguồn dữ liệu:** Bộ dữ liệu cung cấp bởi BTC (không dùng dữ liệu ngoài)  
**Cam kết tái lập:** Có, toàn bộ mã nguồn và pipeline trong repository

---

## Tóm tắt
Bài nộp này hoàn thành chuỗi phân tích từ mô tả dữ liệu, chẩn đoán nguyên nhân, dự báo xu hướng đến giải thích mô hình theo đúng rubric của cuộc thi. Ở phần EDA, nhóm xác định doanh thu chịu ảnh hưởng mạnh bởi mùa vụ và khuyến mãi, trong khi lưu lượng truy cập web chỉ là tín hiệu yếu hơn so với tồn kho và COGS. Ở phần dự báo, mô hình tốt nhất của chúng tôi là một ensemble có trọng số giữa gradient boosting và mô hình mùa vụ năm trước, cho kết quả tốt hơn baseline trên cả MAE, RMSE và R². Phần giải thích cho thấy các biến quan trọng nhất là độ trễ ngắn hạn, mùa vụ theo ngày trong năm và mức doanh thu cùng ngày của năm trước.

---

## 1. Phát hiện chính từ EDA

### 1.1. Descriptive: “Điều gì đã xảy ra?”
Từ các bảng và biểu đồ mô tả, doanh thu có tính chu kỳ rõ rệt theo năm. Q4 thường cao hơn các giai đoạn còn lại do mùa lễ hội và mua sắm cuối năm. Dữ liệu sản phẩm cũng cho thấy sự tập trung vào một số nhóm hàng chủ lực, trong đó một vài danh mục đóng góp phần lớn doanh thu và số lượng bán ra.

### 1.2. Diagnostic: “Tại sao điều đó xảy ra?”
Phân tích nguyên nhân cho thấy doanh thu không chỉ đi theo traffic web mà còn phụ thuộc mạnh vào khả năng cung ứng. Tương quan giữa COGS và doanh thu rất cao, phản ánh vai trò của hàng hóa sẵn có và vòng quay tồn kho. Ngoài ra, tỷ lệ hoàn trả có tính đặc thù theo danh mục và lý do trả hàng phổ biến nhất liên quan đến kích cỡ không phù hợp.

### 1.3. Predictive & Prescriptive: “Sắp xảy ra gì và nên làm gì?”
Dựa trên mùa vụ và các driver đã xác định, nhóm xây dựng forecast và scenario analysis. Các khuyến nghị ưu tiên gồm: tăng cường khuyến mãi theo mùa, tối ưu kênh acquisition, giảm stockout, điều chỉnh mix sản phẩm và giảm hoàn trả bằng size guide tốt hơn. Các đề xuất này đều đi kèm ước lượng ROI để hỗ trợ ra quyết định.

---

## 2. Phương pháp dự báo doanh thu

### 2.1. Baseline an toàn dữ liệu
Baseline sử dụng các mô hình đơn giản nhưng ổn định: seasonal naive theo ngày của năm trước, linear regression với đặc trưng trễ và đặc trưng lịch. Việc đánh giá được thực hiện bằng expanding-window cross-validation theo thời gian để tránh leakage.

### 2.2. Mô hình tối ưu
Mô hình tốt nhất của giai đoạn tối ưu là ensemble giữa:
- Gradient Boosting trên đặc trưng trễ, rolling, calendar và seasonality;
- Seasonal baseline theo cùng ngày năm trước.

Kết quả CV trung bình của mô hình tốt nhất:

| Mô hình | MAE | RMSE | R² |
|---|---:|---:|---:|
| Baseline tốt nhất (M6) | 837,446.12 | 1,134,986.03 | 0.2843 |
| Mô hình tối ưu (M7) | 677,003.83 | 908,371.80 | 0.5784 |

Mô hình ensemble tốt hơn baseline trên cả ba thước đo, cho thấy việc kết hợp tín hiệu mùa vụ dài hạn với động lực ngắn hạn là hợp lý.

### 2.3. Ràng buộc và kiểm soát leakage
- Chỉ dùng dữ liệu cung cấp bởi BTC.
- Không dùng Revenue/COGS của tập test làm đặc trưng.
- Chia validation theo thời gian, không shuffle.
- Submission giữ nguyên thứ tự như `sample_submission.csv`.
- Random seed cố định là 42.

---

## 3. Giải thích mô hình
Phần giải thích cho thấy mô hình dự báo chịu ảnh hưởng chủ yếu bởi:
- `lag_1`: doanh thu ngày hôm trước;
- `doy_profile`: cấu trúc mùa vụ theo ngày trong năm;
- `lag_365`: cùng ngày của năm trước.

Diễn giải kinh doanh: doanh thu gần hạn có tính “bám dính” mạnh, tức là hôm nay thường gần với hôm qua. Đồng thời, nhu cầu thời trang có mùa vụ theo năm, đặc biệt quanh kỳ lễ và giai đoạn mua sắm cao điểm. Điều này phù hợp với thực tế vận hành của doanh nghiệp thương mại điện tử: kế hoạch tồn kho, khuyến mãi và logistics cần được đồng bộ với mùa vụ và xu hướng gần nhất.

Tỷ trọng nhóm đặc trưng trong mô hình tối ưu:
- Nhóm lag: 74.27%
- Nhóm seasonality: 14.02%
- Nhóm rolling: 6.17%
- Nhóm calendar: 3.28%
- Nhóm momentum: 0.85%

Kết quả này củng cố rằng mô hình học được cấu trúc cầu tiêu dùng hợp lý, thay vì dựa vào tín hiệu ngẫu nhiên hoặc leakage.

---

## 4. Hàm ý kinh doanh
1. Cần ưu tiên lập kế hoạch tồn kho theo mùa, không chỉ theo traffic.
2. Khuyến mãi nên tập trung vào các giai đoạn mùa vụ mạnh như Q1, Q3 và Q4.
3. Cải thiện size guide và mô tả sản phẩm có thể giảm trả hàng đáng kể.
4. Tối ưu mix sản phẩm và channel acquisition có thể cải thiện hiệu quả doanh thu trên chi phí triển khai.

---

## 5. Kết luận
Bài nộp đáp ứng cả ba phần quan trọng của Vòng Sơ loại: MCQ, EDA và forecasting. Phần EDA chỉ ra các driver kinh doanh có ý nghĩa thực tiễn; phần dự báo tạo được baseline đáng tin cậy và mô hình tối ưu có cải thiện rõ ràng; phần giải thích mô hình minh bạch, có thể kiểm chứng và gắn với ngữ cảnh kinh doanh. Tất cả pipeline đều tái lập được từ repository.

---

## Phụ lục: Tài nguyên nộp bài
- Mã nguồn và pipeline: repository GitHub của đội
- Submission Kaggle: `outputs/submissions/submission.csv`
- MCQ: `docs/competition/first-round/planning/m2-final-answers.csv`
- Báo cáo kỹ thuật M6–M8: trong thư mục `reports/` và `docs/competition/first-round/`

## Ghi chú xuất PDF
Bản này được viết ngắn gọn để phù hợp giới hạn 4 trang. Khi đưa vào template NeurIPS, nên giữ cấu trúc:
- Tóm tắt
- Dữ liệu và phương pháp
- Kết quả EDA
- Dự báo và giải thích mô hình
- Kết luận
