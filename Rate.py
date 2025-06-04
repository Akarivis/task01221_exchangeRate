from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException


def fetch_rate_data():
    # webdriver的版本为136，谷歌浏览器非136，请自行更新
    driver = webdriver.Chrome(service=Service(executable_path="D:/chromedriver/chromedriver.exe"))
    driver.maximize_window()

    driver.get("https://gushitong.baidu.com/?quotationMarket=foreign&moduleName=quotation")

    # time.sleep(5)  # 强制等待5秒

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "all-stock")))  #等待元素显示

    driver.find_element(By.CSS_SELECTOR,
                        'div.page-module.page-module-blocks > div > div:nth-child(1) > div > div > div.santd-tabs-content.santd-tabs-top-content.santd-tabs-content-no-animated > div.santd-tabs-tabpane.santd-tabs-tabpane-active > div > div > div > div.more-wrapper.c-font-normal.more-text > span').click()

    current_list = ["美元", "人民币"]
    data_list = []
    for currency in current_list:  # 修复变量名错误:ml-citation{ref="6" data="citationList"}
        #保持在顶端
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.HOME)
        xpath = f"//div[text()='{currency}']"
        try:
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )

            # 检查是否已选中
            if "active" not in element.get_attribute("class"):
                element.click()
            else:
                print(f"{currency} 已是当前状态")
        except TimeoutException:
            print(f"切换失败：{currency} 元素未找到或不可操作")

        # 循环参数配置
        max_attempts = 20  # 最大滚动尝试次数（防止无限循环）
        scroll_pause_time = 2  # 每次滚动后的等待时间（秒）

        for attempt in range(max_attempts):
            try:
                # 检测是否存在目标元素（精确匹配文本内容）
                end_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[text()='到底了...']")
                    )
                )
                print("检测到结束标记，停止滚动")
                break  # 找到元素后跳出循环

            except (NoSuchElementException, TimeoutException):
                print(f"第 {attempt + 1} 次滚动...")

                # 方法1：使用 END 键（需焦点在页面主体）
                body = driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.END)

                # 等待内容加载（根据实际网页调整时间）
                driver.implicitly_wait(scroll_pause_time)

        # 循环结束后处理
        if attempt == max_attempts - 1:
            print(f"已达最大尝试次数 {max_attempts} 次，未检测到结束标记")
        else:
            print("正常退出循环")

        # 显式等待父容器加载完成
        wait = WebDriverWait(driver, 10)
        list_items = wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "div.list-item.finance-hover")
        ))

        for item in list_items:
            try:
                # 提取名称（如 "人民币Ethereum"）
                name = item.find_element(By.CSS_SELECTOR, "div.name.c-color").text
            except NoSuchElementException:
                name = "N/A"

            try:
                # 提取代码（如 "CNYETH"）
                code = item.find_element(By.CSS_SELECTOR, "span.code.c-gap-left-lh").text
            except NoSuchElementException:
                code = "N/A"

            try:
                # 提取市场类型（如通过 SVG 路径判断）
                market_label = item.find_element(By.CSS_SELECTOR, "path#FX").get_attribute("fill")
                market = "外汇" if market_label == "#7C1EFF" else "其他"
            except NoSuchElementException:
                market = "N/A"

            try:
                # 提取其他属性（如 data-id）
                data_id = item.get_attribute("data-id")
            except NoSuchElementException:
                data_id = "N/A"

            # 将数据存入字典
            data = {
                "名称": name,
                "代码": code,
                "市场类型": market,
                "data-id": data_id
            }
            data_list.append(data)

    #打印结果（或保存至文件）
    for entry in data_list:
        print(entry)

    driver.quit()  # 确保关闭浏览器
    return data_list
