from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "scans" (
            "id" SERIAL NOT NULL PRIMARY KEY,
            "status" VARCHAR(30) NOT NULL DEFAULT 'uploaded',
            "analyzed_at" TIMESTAMPTZ,
            "document_date" VARCHAR(10),
            "diagnosis" TEXT,
            "drugs" JSONB NOT NULL DEFAULT '[]',
            "raw_text" TEXT,
            "ocr_raw" JSONB,
            "file_path" TEXT NOT NULL,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "user_id" BIGINT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS "idx_scans_user_id_d51f17" ON "scans" ("user_id", "id");
        CREATE INDEX IF NOT EXISTS "idx_scans_user_id_8ef2cb" ON "scans" ("user_id", "created_at");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "scans";"""


MODELS_STATE = (
    "eJztXetv2zgS/1cEf9kUSFvLbxuHA5I0uc1tHkWS7i22KQSKohNdZMmrRx+36P9+JEW9KN"
    "lWbNJ2FH5palmeIYePGf5mOPN3a+ZZyAneffCjh9ZE+7sF5nP8lz1uHWotF8xQ9iR+ET8O"
    "genQ5xZ+QF+0XQt9RwF+9vkL/jgDLnhAFv7oRo6DHwAzCH0AQ/xkCpwA4UfzJ2NqI8einB"
    "NGtkWoRa79V0Q+h35EXrXQFEROmJGL2VnZG+Q5a1RC3zIN6DnRzM3oWh7EzbDdh4zSA3KR"
    "D8I8LdoqI/wxpy06d8Mz2kz8DfRc0g3bDQPa6gfyxtuO3hv2Rt1Bb4RfoU1Inwx/0tYH0L"
    "fnoe25Gd/5j/DRc1MumGQrbnPGPeZB23B11/r5k+tA6z6C/aF1H1m90Ui7j8wxHOFHHdDD"
    "j/RuWyN/ehA/Gg7xIxPpPe3g9ObDRKOj9obwm7IxyAauM+OeeB2Pe2KBEOQeZYNH/+aHLx"
    "2KxeOXvLJqABPaK4Yw+W1xDE8egb9wEGfgu+Eg9yF8JCPX79cdMkxkyZD9fnRz8uvRzQEm"
    "SCXt4dkfr5kr9lUn/o6MayZCvHCiKV4nkY98AaJM1k9ekjyLBkr0S4mhiMUSj4UReg8ofM"
    "SyY8vBBPDpG/Ato7CYsiGd+1lLAoFjus6wHbO2nv12gxxAZVMev7rDxZTCx1z/WslkSwiy"
    "9v4sCIrbUgg/RusWAreWJqIv5jVRgB/wmuhzKwqQb8R7P/4XN6LwCPqISMsAYeuL0lrb01"
    "pwjNeeCTtj/P9Ru6clCxGiMflgdiFZgqDfo8uRLlcAyE+6w9G9e+++1YIQhFEw0aK54wEL"
    "WfiVjj7uaHPfgygIMKvkieW5KPl/NLeIzJKPAfiKP7zHorcdZBGydK1PtOuTG7IfdNtkP+"
    "hMdcy5p0Mt2UJM3EDSpFE/bhnuhjnqW9rBv2+vr8gj2G2Td6e9N4SoB33DB98m2hXm5zPi"
    "cGC1yZtT0js47BMenWk/plFWzdlUI9NXpI6tt4vgMcfLDoXx3n90e3L04ZS0AvcrXQ75lV"
    "WcjGeej+wH9zf0g87JczwdgQvR5lvPJyaMhVvORuZMPMlWCLuVTMFWbZHnV3jGQ7Ia7rbF"
    "auFue6ESJl8VrRq8rzo//hfvtGvOXRCFnuF63+rbORzTteT7AX8b2jO0SMZ1ZWoxOu+S/7"
    "RyXTKAZRXnR5Xg784vT2/vji4/kp/OguAvhzbw6O6UfNOhT39wTw8G3CClRLT/nN/9qpGP"
    "2p/XV3Qtz70gfPApx+y9uz+5ocRijGbIDQ3SE0kWaomH5LWhC14b+uK1oZfWhmWDB9cLbJ"
    "GmYUGYefprCfIOfV9oTIgR3N3pH3eFaZ0I7ODy6I83hal9cX31r+T1nIBPLq6PecEm2MSy"
    "3fsf08iFpOWaGdlOaLvBO8cOwn+ut5unLNeSM1H9m8r5k4u//WzZMDzUSEe+LJE64bdc6r"
    "yAuV2CEOClTiyCEE8YSbM5T/41TWZmREqSao766525U3wKMOYAawSB5nVeygUGr2ny5s7Z"
    "Uqy/SmkXmUqx/lqYhXXtOj/YshJpDWbLdI+NQXagFjOwNTGRIk81rlLGNTvJy9gIc+TXGr"
    "/9AbeqgeZN8K1nA801kVUKldRBVhNMJUVWyWgpH9/u0NI2IDDkgMCMcDhuF2YL81HQIZLg"
    "0EMzYDtyBislLfls3xN8tu8tPtv3Smf7BjhE9bZwcGQZOlIWoQ2fBImx6uSTJy9Zkn3Bgu"
    "wvlmO/JMY5po8MN5qZYt0HeVnyPGTPTF3wxNQXz0udl6dp++GjTAy0yGBtM1cocL1EiMQY"
    "5USEG2hJC2LIiK89y07xTF3ljyrOuEFZaq3Lo4vTiUb+vXfPTuNP8d/WuhORt+ezeTjgp6"
    "HvOasmYOvT7enNenBmQn2LIq6IFaEdmGjk33v36MPl+dVEo3/WFvDi+JFSPI4dGNiitb+u"
    "kjKbo8+XcYHBejEdHh4m4G660k1MZonsjq+vLwqH0uNzHvn5dHl8irdRKlz8kh17ixO7Nh"
    "8Q41EozJ7h84MR+Y6kPaKSj3QlL1zLL1PzJT3vgCA0HO/BdrfnaC3yVH5WIRCMwkybiq0p"
    "zLQx41oN/z0LsFkzqBRL6NHACu6rbTF0brsBYfLDSgkOeYR7+ZF1spVMaj7Oq2haiI213T"
    "up1Aq2LeiRRxCaXmgEJCyyoUI5ift4G3exlljScOGmySIJjF4pgUcEHLyHwEcEn4i/nVhw"
    "jZTIr7SjJ0k/L7yHWvKZYlMo8pERuGAePHphI2VDNtmzuKO3rJ+1hOMj6M1myLVAY3fam0"
    "IX15CKYYIQr65XIJxj0tF1JDRFyCKWziuQ0Rnrai0xxYiQ8QpWGbXyaG9rrrcl7u7C4dlC"
    "bmgDkdDSJiK7dtGdh/8RK7iTQjdXm4KR75OoaqbZ9uUumiTZxJ09y/W1ej7lYiSOkG9Dgu"
    "KtjpJgrx7m4iRA+kgFSmw9UIIREhv+8BUfrdmElOEvzZFv4B3cgj7Dq0mSEBnphkdB4MaF"
    "yBURVF+N+2bkX1f8dxnAY42TEYL3wQ4QCFAt/ZK8m1cwVvxMxeLtLhaPZg0woaU/L4UAGz"
    "iVcmMflZMNLdxpS1YgT568bEkKVlKdxTqqU77HWASmZdxk5KDvht+gqXYuCdiB1nQ5PUQ2"
    "Vk2220xEiyncfyWd3Im7qcmpXQq06phAPPPUDipJXRlDe3HeVklKnp+kpJgJILX5t7qPFO"
    "R2e3qnXX26uCgJjrVuu7LLHYNWi48lJ9xH2eGmbVlwTBhyMuNYHp4I0IuEIBLVGUDyDF74"
    "JcFi+hTcMTCTLbqMQ5MvtdCuYhFKFWVCv8lnN7zr+FIz+hQZvMTbLMi1ZAooT/4likeFKz"
    "corLXCKBWTDaA6P1WeQZNUfWb0yRBbRr1BMlOJJ2oKTYzjKgd9uCF4Qo2NAb1Elg0prXPa"
    "0bpBoDM08xopkDy4dok7uSm6x0KwL1EQALoSVuN73E8OcwhfErQ+i79TIN8OczX3h/eRab"
    "WHWpqypmNB6ohoM+cCP1rL0hcHWYz+HoKDrHXbhWpq3l7YGLQJRN3Hr5z+weYX8l/AQXmW"
    "bVYyhJgj33Tvpjo8voLDY3E/lbPt5Dk0zqjfRAPLCGHjdNUzzLyceiuZefm7icrM272Z12"
    "237yNr0KeZC/UuiTHR+yNuriWDpopV7EuxCl+mDl2I6qsCC2J1JrGjtzuMeY5qEIUMosIx"
    "xZk8z9dGa2KgebSpaXhfGWxbnSIhms2AbzdaHswqvaVd/bEpCMpdYa1jHZdvvabWccXt30"
    "W17Ug2C/JfVcVueyYzgDqpAgch3ZescY8m/iZV4gA02+TfKWSbFDeSymIWHTnJ5+oQ6HMV"
    "GQbIN3P70lwn14eZZHfYwzlJ27ZdMT4n9cXGpzouXwZtiri5Xcj1Ws2pyeGDgRf5UFrEW0"
    "pcXU3eQIyb3kx+oR6RAOLtS9bMTGivJdAzxwMbS3RKiCyR6YfrT8cXp9rHm9OT89tzdtc7"
    "PbbTL6nZmyYZvjk9uihnbg6w/oCkM3IEyXF4HcmbfeA+yVJBjPQLhzS4wOrVJYQ3CKreTu"
    "3gnWppanYZ4lKxVEmyxKPJAp373mweSpZomUmTRYpmJrIs3DdjG7N1CbdGC/n73Pbj08lW"
    "vSM8W+UiEeIiUUE/TQ36YWD0M0e1DCZXH15AQ4J9ShCbRH9hnn6DxLYAT5WgchdwapAslc"
    "e6ptAqPdYbOoPWdFir9MlL0yenhWubJhqRSZP5GsG5nMJ1/NflNMSFusFGlolZaHRn1W4l"
    "zF/dnL2K68GC4jSoR5KFQRJmY8LRiATbdElRajjS++TRtJerWpMf0Tf37r1LV1lF5jG26e"
    "kTkqkMWG26C8Jeyfddx0e2xD++0ahvwzuepLfedjTpQp/iHATBNw9vBI8gEOrXLeA/PJOG"
    "J5FM+yu0vFddsK2auQIq1j7PVoclCt07n2331VTivyMYev4HD0YzRHeE1Uqc+0leiX+lXx"
    "kW+05d0diZ5jYh0NM0n3A4ovMOkHnX74zJVDTj0Fg9OWjwQ0e19Vt8/pgiH2EdRPlOtF+S"
    "BBxpfs9fDrVf0rjaODLyF8KgN9WLBGxrQhR/n6r8znRcaQXAYX+k2Rb5ZQpcTzS93x2QM1"
    "KHtHlg0bWUdfDgeo7co3MtRN/Dt+mv3nbfBjPgOKwtErIpF2UjSzeWuTQ8RCQ/Y+QLtSGW"
    "+4tJ/v9CQ2zSbUWWXAsMXldZBeXnaaifp9Iu3twykWULl5J617GGqzKB8zU4jGIydGUR77"
    "YaRwq9A3oSY+Znj9ySN4fD2CAdFVPh50Zw2X0McTmZZYBOe5mTeWMrHGJRPHjxdSwpBk+O"
    "fsMtb2U6qnw1yqRZatJIS3ZaOYqNynZajZKK1MoyjMJS6sM6RmFVvsTKgiRGmjJSGYV7Vp"
    "VkzhWU2UODrjCTtmrV1S71s5FpRxaHkdcSW1KeJb7KNyZEYaLpFJ/lBSymysjrlPhrMi4D"
    "rAANqXLlOLwm4Vbsr1KiH8psGmfqMVoyLDQa3xaFjx9976ttUaL1ItEKPzrkY9HwDvtozN"
    "nXykTbHW6njyBN4kTiY81RH5L4sOmInQfwn/6UgMdda7wwkKI4lHXi0K64ODTtgHiuaRMq"
    "4jo6+rhDW4LoYQVBLWGmkrfsRbrDeW6Vy9nBM/pNvlSX9NOQHP9fxafhIYEKJWwoSqiuym"
    "yEDwrX/rKAwl8RcMLHk0cEn0jkBKkZU8cQrfhZ3hR9pF8bMPk+rbmzKLkfLcaGm/y5lZRl"
    "Y4kfVLa/nd6bgAzDHrdzQPeQ2ptk0sampjkG3DynQZhkJMn7qEuA8XEMj3dh/CKNqewTEH"
    "2E6IqAJinw3h7AmF5a8r1jxqHGQ5ogdQTfE1oEdycGLmETT5SJZnku0t5rwZM9nyMaikmn"
    "H9UT8bepxQyGPQ3vx4dpYCdegpA9v/LiaAhl/grMXRii2dwBQgpLypBc0rztSo/bQ+9yMp"
    "JznlintGfNDfEll/UUlr+oUjJbS2C005pB2VYr5xxQmTavwFM5O4TY/epA19QDncg7e3Uv"
    "Gcu/qvfqx5WzXWSoMI7FCz+wK5RDGMoh6rwoC9yoqohbB91YUEk3hTdm6feGXawpXMA32H"
    "cK0djhfdJpP56hKRCBZ53FcLbqYaSOttOP5ye9g8r5zDCEUaf/fjls8Z5cGEUUB+ySOMHx"
    "oP1Gi0vaxfdBJwSkyE2SSfUC4uAOxwsNPJTImdSATTqA4i2DKelLn9zjhmhAWgZHOmkFbh"
    "/9QJel3tPfJ7wZajNq995wrSTKEk8F/NEVAaiogLWdB6xx+5QEeIDj8CJRgnTdyYpYKjCQ"
    "DBZ0BYMF3cVgQbcEFnCbyfYQgwrGCjYQcgppCIa20zAFBb009IiuoJdmjqsKtBWJJqx1Vp"
    "OFHFQVwKqDHCwonLWg3qFBcxar6/U7DHnIp7E1IT3zorTwavVoUYAgDayNM6LRBFAcOTiI"
    "PwCLHIu77fRKoGmSUCCSS4K81GsXMujSVBIwzihBskcNe1CFI+xDNK6PsGTQV+AYhHKIHk"
    "Tc3a+uUlfFqOGX+LNOh97ckFZ9qczlhavSahk6YGZaQLoQMzbNLrPmOLO4DI0kiRboN3yh"
    "k74ShyLpUCSt/l8Fl1cwRfE4h94TcmUVYyszadDuqeCXhh7TlZN/k2P5WiekZx/LF1WDbm"
    "RpCwkFLSLfR3gexRV84nGtVdWC+91hqbRF/IIxzb2h6lvsGrQox91YgzZNQw3iixXklgVe"
    "sqNCXnZuKNMLxVhMcfoi7eNv2gFfyyL26Q8swhbqFOPo0zADRCN5IEU6hp12HNiwXr5qVf"
    "pCYOmLpIzXfwOxARVVpcISHq8pvYby5jTHTKwb1rjO9irLNUF2Bqawb1mlvtr6nv9dSd/z"
    "NQCVa2KvtHw285JAP7MNidesPR3mJ2NpGJnPouifaFtWHJxIqZGUhSwqkDkzKsJ7sQlAwg"
    "1pesPxkFIZxRc7QV+5KfbBTaHUv1z1r2CiBul/BRNJvAuygbbaK/womb3NhI9O4iJYtygI"
    "MLXbuBRWLYOy+pd5kzItsBW/wgpt2SrgZZd56eI6JbGFF0eo9IdJlNXCAWP2o9lt0zQcfX"
    "ovZTQieWtGFAKyBrCnHZ0zIClvXGYp6FJuSyxFxnlPjcVELlu1F4vrTJ7lGGQrWEoQd0Ze"
    "2YvKXnzx9mJxL5CyYgocGmk1rqmNZGFrRdPqDCGL/KiWNbTgp4eLg3+nuXeUMbTz6N/4uM"
    "JKd8CuXu3hTgYtAdS4Y09m/6SkyZSOa7/GxlN/yIwnM72Siyf+e+pSo49M9oiVgKVudz2O"
    "MdYLofFLzCi/dEbYQ2uKE+1WjaqahygeINhTSTYPxIxXWcxVknotMVGXC5UZ+uLM0MpNVE"
    "7x6QpGL9woVfivlDDBZ5pSsqz5RQk210hwnE/OuTjLcZIoS+GbOzPpF2abWpEpx9JJVJvV"
    "p7f0xibJl2PSIn/sLb3bTkz+QXs00bJreuwtMteJaX4Yp7waZp8yPsRsb49oDh5Le/fuXc"
    "mA39hwEpWgpHLGbCs5ya6vqNiBgdel/XWV5ckWx/MFWWCwnl/J8xwE3E3xUBOTWSK/4+vr"
    "i4J1c3zOI56fLo9PsYCpeLMLKmXtGnh+aHj+6mom7bUkWiT/whWssttfgd2uwkibM66VFr"
    "FMS2SD+IgkU2XTLtVUVyTZ9GLNEVXTHFhYN9q28seHpYp99C2jIm5FnSD2Je520IdZpGx2"
    "0s2X66kcxSRVSD58vOwyIP4BslOM6HlCH44oE/ruWNfv06JBOcaEZ1zCr8cdq7WryRVmi1"
    "uWEDY7+CXbomWH4OCeJSClV3fusNnk2QGifSSuONxT6mnoxZlOSbMThwXlTrwbS9wOCiLn"
    "toBajgXlrBEX8bbR6RkEAW7/tq1tjqsyyxRMvndKUsHk8sKk1zYuxOLmP/8PG1MVTQ=="
)
