## 背景需求

AWS 发布了[成本和使用报告 （CUR），](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/billing-reports-costusage.html)提供有关您的成本的全面数据。AWS 还提供成本资源管理器来查看您过去 13 个月的成本。这些资源非常有帮助，但如果您想要分析过去几年的计费数据，该怎么办？如果您想要一个自定义的方法来显示您的业务需求的数据，该怎么办？

目前AWS已经提供了基于quicksight的解决方案，[基于 QuickSight 的成本可视化方案](https://aws.amazon.com/cn/blogs/china/cost-visualization-solution-based-on-quicksight/)， 但是客户希望完全使用国内服务进行分析，并且可以复用现有资源情况，所以在下面的文章中，我将向您展示如何将成本和使用报告数据导入Amazon Elasticsearch，然后创建您自己的 Kibana 仪表板。本次测试文档由于我的账号没有CUR权限，所以在海外region进行测试，但是经过客户确认，国内也是可以使用的。



## 解决方案概述

### 使用该解决方案可以实现如下的需求：

- 这个月账单？ Monthly Billing
- 账单费用的分布、组成简单分析？Cost Explorer
- 账号资源是不是充分利用了？Trust Advisor
- EC2挑选的合理吗？Computer Optimizer
- 怎么样买RI/Savings Plans最好？ Recommendations
- RI/Savings Plans的使用率/覆盖率？ Reservations & Savings Plans Utilization & Coverage 

### 方案的具体架构如下：

![image-20211115224655435](https://tva1.sinaimg.cn/large/008i3skNgy1gwg7xrae4gj31om0okacq.jpg)

开启了CUR后，每天AWS自动会将CUR报告保存到S3，然后lambda函数去抽取S3的数据并写入到ES。



## 具体步骤：

#### 1. 开启CUR。

注意：报告名称不要包含减号“-”，按照如下截图勾选“包括资源ID”及“Amazon Athena”

![image-20211115225922671](https://tva1.sinaimg.cn/large/008i3skNgy1gwg8ar7swrj31500u0myk.jpg)



![image-20211115230006453](%E4%BD%BF%E7%94%A8es%E5%88%86%E6%9E%90cur%E8%B4%A6%E5%8D%95.assets/image-20211115230006453.png)

#### 2. 配置lamdba的iam策略。

配置lambda的iam策略，需要有两个部分的权限，

1. 能够下载CUR所在的S3桶的权限。

2. 能够访问ES所在的域并往里面写入数据。

对于s3桶名为robertxiao-CUR的桶，需要添加如下的iam策略。

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::robertxiao-cur/*",
                "arn:aws:s3:::robertxiao-cur"
            ]
        }
    ]
}
```

对于ES，需要将lamdba的执行role加入到es的内部用户中。

#### 3. 配置Elasticsearch

创建ES的domain，也可以复用现有的es集群。

![image-20211124222714885](%E4%BD%BF%E7%94%A8es%E5%88%86%E6%9E%90cur%E8%B4%A6%E5%8D%95.assets/image-20211124222714885.png)

到kibana里面将lambda的角色加入到all access权限的组里面。（这个权限可以设置的小点，这里为了测试）

![image-20211124230242989](%E4%BD%BF%E7%94%A8es%E5%88%86%E6%9E%90cur%E8%B4%A6%E5%8D%95.assets/image-20211124230242989.png)



#### 4. 配置lamdba

首先创建层文件，需要包含如下的包。也可以使用已经现成的文件

```
boto3==1.17.100
botocore==1.20.100
certifi==2021.5.30
chardet==4.0.0
elasticsearch==7.13.1
idna==2.10
jmespath==0.10.0
python-dateutil==2.8.1
requests==2.25.1
requests-aws4auth==1.1.1
s3transfer==0.4.2
six==1.16.0
urllib3==1.26.5
```

#### 5. 配置Elasticsearch的dashboard

![image-20211125095816000](%E4%BD%BF%E7%94%A8es%E5%88%86%E6%9E%90cur%E8%B4%A6%E5%8D%95.assets/image-20211125095816000.png)

